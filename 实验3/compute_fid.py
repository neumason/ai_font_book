# -*- coding: utf-8 -*-
"""
实验3：同一汉字不同字重图像的 FID（Fréchet Inception Distance）比较
====================================================================
对思源宋体 5 个字重（Light / Medium / SemiBold / Bold / Heavy）的
"永"字图像，以最粗的 Heavy 为基准计算 FID。

FID 是分布级指标：它把一组图像的 InceptionV3 特征拟合成多元高斯
N(μ, Σ)，再比较两个高斯的 Fréchet 距离：

    FID = ||μ1 - μ2||² + Tr( Σ1 + Σ2 - 2·(Σ1·Σ2)^{1/2} )

每个字重只有 1 张图，无法直接构成"分布"，故采用图像块（patch）采样：
从每张 500×500 图像上以 stride 滑窗提取 128×128 图块，仅保留含墨色
（覆盖率 ≥ 2%）的图块，缩放到 299×299 后提取 InceptionV3 pool3
特征（2048 维），以全部图块的特征集合作为该字重的特征分布。
图块网格位置在所有字重间一致（图像已对齐），保证分布可比。

小样本偏差控制（每种特征版本均做）：
  ① 对半拆分地板：Heavy 图块随机对半（69 vs 69）的 FID，重复 20 次——
     同分布、半样本量下的 FID 基线；
  ② 自助法地板：从 Heavy 中有放回重采两组同规模样本（138 vs 138）的
     FID，重复 20 次——同分布、满样本量下 FID 的下界估计。
  此外给出共享 PCA 50 维特征的 FID 作为稳健性对照（低维协方差估计
  在小样本下更可靠）。

输出（保存在 结果/ 目录下）：
    FID_基准对比.csv     各字重 vs 基准 Heavy 的 FID（2048 维 / PCA50）
    FID_矩阵.csv         5×5 两两 FID 矩阵（2048 维）
    噪声地板.csv         两种地板估计的均值与标准差
    FID_以Heavy为基准.png 基准 FID 柱状图（含噪声地板参考线）
    FID_热力图.png       两两 FID 热力图（2048 维）
    FID_特征PCA.png      图块特征的 PCA 分布散点图
    图块采样示意.png     各字重参与 FID 的图块样例
"""

import os
import sys

import numpy as np
import pandas as pd
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import torch
import torch.nn as nn
from torchvision.models import inception_v3, Inception_V3_Weights

sys.stdout.reconfigure(encoding="utf-8")

# ----------------------------------------------------------------------
# 0. 路径与参数
# ----------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "结果")
os.makedirs(OUT, exist_ok=True)

WEIGHTS = ["Light", "Medium", "SemiBold", "Bold", "Heavy"]
FILES = {
    "Light":    "思源宋Light.png",
    "Medium":   "思源宋Medium.png",
    "SemiBold": "思源宋SemiBold.png",
    "Bold":     "思源宋Bold.png",
    "Heavy":    "思源宋heavy.png",
}
BASE_W = "Heavy"          # 基准字重

PATCH = 128               # 图块边长
STRIDE = 32               # 滑窗步长
INK_MIN = 0.02            # 图块墨色覆盖率下限（排除纯白底图块）
INCEPT_SIZE = 299         # InceptionV3 输入尺寸
BATCH = 64
SPLIT_REPEAT = 20         # 噪声地板估计的重复次数
PCA_DIM = 50              # 稳健性对照的 PCA 维度
RNG = np.random.default_rng(42)

zh_fonts = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
avail = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.sans-serif"] = [f for f in zh_fonts if f in avail] + \
                                  plt.rcParams["font.sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


# ----------------------------------------------------------------------
# 1. 读图与图块采样
# ----------------------------------------------------------------------
def load_gray(path):
    """读图并合成到白色背景，返回 uint8 灰度数组。"""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return np.asarray(im.convert("L"), dtype=np.uint8)


def extract_patches(gray):
    """滑窗提取图块，仅保留墨色覆盖率 ≥ INK_MIN 的图块。"""
    H, W = gray.shape
    kept = []
    for y in range(0, H - PATCH + 1, STRIDE):
        for x in range(0, W - PATCH + 1, STRIDE):
            p = gray[y:y + PATCH, x:x + PATCH]
            if (p < 250).mean() >= INK_MIN:
                kept.append(p)
    return kept


patches = {}
for w in WEIGHTS:
    g = load_gray(os.path.join(BASE, FILES[w]))
    patches[w] = extract_patches(g)
    print(f"{w:9s}: 保留图块 {len(patches[w]):3d} 个")


# ----------------------------------------------------------------------
# 2. InceptionV3 特征提取（pool3, 2048 维）
# ----------------------------------------------------------------------
print("\n加载 InceptionV3……")
model = inception_v3(weights=Inception_V3_Weights.IMAGENET1K_V1,
                     transform_input=False, aux_logits=True)
model.AuxLogits = None
model.aux_logits = False
model.fc = nn.Identity()          # 输出 pool3 的 2048 维特征
model.eval()


def patch_to_tensor(p):
    """uint8 灰度图块 -> (3,299,299) 张量，归一化到 [-1,1]。"""
    im = Image.fromarray(p, mode="L").convert("RGB")
    im = im.resize((INCEPT_SIZE, INCEPT_SIZE), Image.BICUBIC)
    x = torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0)
    x = x.permute(2, 0, 1)
    return x * 2.0 - 1.0


@torch.no_grad()
def features(patch_list):
    """提取一组图块的 InceptionV3 pool3 特征，返回 (N,2048)。"""
    feats = []
    for i in range(0, len(patch_list), BATCH):
        x = torch.stack([patch_to_tensor(p) for p in patch_list[i:i + BATCH]])
        f = model(x)
        if isinstance(f, (tuple, list)) or hasattr(f, "logits"):
            f = f.logits if hasattr(f, "logits") else f[0]
        feats.append(f.cpu().numpy())
    return np.concatenate(feats, axis=0)


feats2048 = {w: features(patches[w]) for w in WEIGHTS}
for w in WEIGHTS:
    print(f"{w:9s}: 特征 {feats2048[w].shape}")

# 共享 PCA 基（在全部字重的联合特征上拟合），用于 50 维稳健性对照
allF = np.concatenate([feats2048[w] for w in WEIGHTS], axis=0)
mean_all = allF.mean(axis=0, keepdims=True)
_, s, vt = np.linalg.svd(allF - mean_all, full_matrices=False)
proj = vt[:PCA_DIM].T
var_ratio = (s ** 2) / (s ** 2).sum()
print(f"PCA{PCA_DIM} 累计方差占比: {var_ratio[:PCA_DIM].sum():.1%}")
featsPCA = {w: (feats2048[w] - mean_all) @ proj for w in WEIGHTS}


# ----------------------------------------------------------------------
# 3. FID 计算
# ----------------------------------------------------------------------
def gaussian(f):
    mu = f.mean(axis=0)
    sigma = np.cov(f, rowvar=False)
    return mu, sigma


def fid(f1, f2):
    """标准 FID：||μ1-μ2||² + Tr(Σ1+Σ2-2(Σ1Σ2)^{1/2})。"""
    from scipy import linalg
    mu1, s1 = gaussian(f1)
    mu2, s2 = gaussian(f2)
    diff = mu1 - mu2
    covmean = linalg.sqrtm(s1 @ s2)
    if isinstance(covmean, tuple):
        covmean = covmean[0]
    if not np.isfinite(covmean).all():          # 数值兜底：加微小抖动
        eps = 1e-6 * np.trace(s1 @ s2) / s1.shape[0]
        covmean = linalg.sqrtm((s1 + eps * np.eye(len(s1))) @
                               (s2 + eps * np.eye(len(s2))))
        if isinstance(covmean, tuple):
            covmean = covmean[0]
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    return float(diff @ diff + np.trace(s1) + np.trace(s2)
                 - 2.0 * np.trace(covmean))


def floors(f_base, tag):
    """两种小样本噪声地板估计。"""
    N = len(f_base)
    half_vals, boot_vals = [], []
    for _ in range(SPLIT_REPEAT):
        idx = RNG.permutation(N)
        h = N // 2
        half_vals.append(fid(f_base[idx[:h]], f_base[idx[h:2 * h]]))
        i1 = RNG.integers(0, N, N)
        i2 = RNG.integers(0, N, N)
        boot_vals.append(fid(f_base[i1], f_base[i2]))
    r = {"特征": tag,
         "对半拆分地板均值": round(float(np.mean(half_vals)), 3),
         "对半拆分地板标准差": round(float(np.std(half_vals)), 3),
         "自助法地板均值": round(float(np.mean(boot_vals)), 3),
         "自助法地板标准差": round(float(np.std(boot_vals)), 3)}
    print(f"[{tag}] 对半拆分地板 {r['对半拆分地板均值']}±{r['对半拆分地板标准差']}　"
          f"自助法地板 {r['自助法地板均值']}±{r['自助法地板标准差']}")
    return r


print(f"\n估计噪声地板（{BASE_W}，×{SPLIT_REPEAT}）……")
floor_rows = [floors(feats2048[BASE_W], "InceptionV3-2048维"),
              floors(featsPCA[BASE_W], f"PCA{PCA_DIM}维")]
df_floor = pd.DataFrame(floor_rows)
df_floor.to_csv(os.path.join(OUT, "噪声地板.csv"), index=False,
                encoding="utf-8-sig")

# 各字重 vs 基准 Heavy
rows = []
for w in WEIGHTS:
    if w == BASE_W:
        continue
    d1 = fid(feats2048[w], feats2048[BASE_W])
    d2 = fid(featsPCA[w], featsPCA[BASE_W])
    gap = abs(WEIGHTS.index(w) - WEIGHTS.index(BASE_W))
    rows.append({"字重": w, "基准": BASE_W, "字重间隔": gap,
                 "图块数": len(patches[w]),
                 "FID_2048维": round(d1, 3),
                 f"FID_PCA{PCA_DIM}": round(d2, 3)})
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "FID_基准对比.csv"), index=False, encoding="utf-8-sig")
print("\n", df.to_string(index=False), sep="")

# 两两 FID 矩阵（2048 维）
M = np.full((len(WEIGHTS), len(WEIGHTS)), np.nan)
for i, a in enumerate(WEIGHTS):
    for j, b in enumerate(WEIGHTS):
        if i != j:
            M[i, j] = fid(feats2048[a], feats2048[b])
pd.DataFrame(M, index=WEIGHTS, columns=WEIGHTS).to_csv(
    os.path.join(OUT, "FID_矩阵.csv"), encoding="utf-8-sig")

# ----------------------------------------------------------------------
# 4. 图 1：基准 FID 柱状图（2048 维 / PCA50 双面板，含地板参考线）
# ----------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
labels = [f"{r['字重']}\nvs\n{BASE_W}" for _, r in df.iterrows()]
for ax, col, fl, ttl in zip(
        axes,
        ["FID_2048维", f"FID_PCA{PCA_DIM}"],
        floor_rows,
        ["InceptionV3 pool3（2048 维）", f"共享 PCA {PCA_DIM} 维"]):
    ax.bar(labels, df[col], color="#4C72B0")
    for k, v in enumerate(df[col]):
        ax.text(k, v, f"{v:.2f}", ha="center", va="bottom", fontsize=10)
    ax.axhline(fl["对半拆分地板均值"], color="#C44E52", ls="--", lw=1.5,
               label=f"对半拆分地板 {fl['对半拆分地板均值']:.2f}")
    ax.axhline(fl["自助法地板均值"], color="#DD8452", ls=":", lw=1.5,
               label=f"自助法地板 {fl['自助法地板均值']:.2f}")
    ax.set_ylabel("FID")
    ax.set_title(ttl)
    ax.legend(fontsize=9)
fig.suptitle(f"以 {BASE_W} 为基准的 FID（值越大分布差异越大）")
fig.tight_layout()
fig.savefig(os.path.join(OUT, f"FID_以{BASE_W}为基准.png"), dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------
# 5. 图 2：两两 FID 热力图（2048 维）
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(M, cmap="viridis")
ax.set_xticks(range(len(WEIGHTS)), WEIGHTS)
ax.set_yticks(range(len(WEIGHTS)), WEIGHTS)
for i in range(len(WEIGHTS)):
    for j in range(len(WEIGHTS)):
        if not np.isnan(M[i, j]):
            ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center",
                    color="w", fontsize=9)
ax.set_title("各字重两两比较：FID（2048 维）")
fig.colorbar(im, ax=ax, fraction=0.046)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "FID_热力图.png"), dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------
# 6. 图 3：图块特征 PCA 分布散点图
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 6.5))
colors = ["#937EB0", "#4C72B0", "#55A868", "#DD8452", "#C44E52"]
for w, c in zip(WEIGHTS, colors):
    P = featsPCA[w][:, :2]
    ax.scatter(P[:, 0], P[:, 1], s=10, alpha=0.45, color=c, label=w)
    cen = featsPCA[w].mean(axis=0)[:2]
    ax.scatter(cen[0], cen[1], marker="*", s=260, color=c,
               edgecolor="k", zorder=5)
ax.set_xlabel(f"PC1（方差占比 {var_ratio[0]:.1%}）")
ax.set_ylabel(f"PC2（方差占比 {var_ratio[1]:.1%}）")
ax.set_title("各字重图块的 InceptionV3 特征分布（PCA，★为分布中心）")
ax.legend(markerscale=2)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "FID_特征PCA.png"), dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------
# 7. 图 4：图块采样示意（每字重 6 块）
# ----------------------------------------------------------------------
fig, axes = plt.subplots(len(WEIGHTS), 6, figsize=(9, 8))
for i, w in enumerate(WEIGHTS):
    show = patches[w][:: max(1, len(patches[w]) // 6)][:6]
    for j in range(6):
        axes[i, j].imshow(show[j], cmap="gray", vmin=0, vmax=255)
        axes[i, j].axis("off")
    axes[i, 0].set_ylabel(w, rotation=0, ha="right", va="center", fontsize=11)
fig.suptitle(f"参与 FID 计算的图块样例（{PATCH}x{PATCH}，stride={STRIDE}，墨色≥{INK_MIN:.0%}）")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "图块采样示意.png"), dpi=150)
plt.close(fig)

print(f"\n全部完成，结果已保存到: {OUT}")
