# -*- coding: utf-8 -*-
"""
实验1：同一汉字（永）不同字重图像的相似度指标比较
====================================================
对思源宋体 5 个字重（Light / Medium / SemiBold / Bold / Heavy）的
对齐图像两两计算 6 种指标：

    MAE   平均绝对误差          （越小越相似）
    MSE   均方误差              （越小越相似）
    RMSE  均方根误差            （越小越相似）
    PSNR  峰值信噪比            （越大越相似，单位 dB）
    SSIM  结构相似度            （越大越相似，范围 0~1）
    LPIPS 感知相似度(AlexNet)   （越小越相似）

输出（保存在 结果/ 目录下）：
    单图统计.csv          各字重的墨色像素占比、平均灰度
    成对指标.csv          10 个字重对的全部指标
    指标矩阵_*.csv        各指标的 5×5 矩阵
    热力图_*.png          各指标的成对热力图
    以Heavy为基准指标.png  各字重与基准 Heavy 的 6 指标柱状图
    字重对比与差异图.png  5 字重原图 + 各字重与基准 Heavy 的差异放大图
    diff_图像/            每对图像的绝对差放大图
"""

import os
import sys
import itertools

import numpy as np
import pandas as pd
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from skimage.metrics import structural_similarity as ssim_fn
import torch
import lpips

sys.stdout.reconfigure(encoding="utf-8")

# ----------------------------------------------------------------------
# 0. 路径与参数
# ----------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "结果")
DIFF_DIR = os.path.join(OUT, "diff_图像")
os.makedirs(DIFF_DIR, exist_ok=True)

# 按字重由细到粗排列
WEIGHTS = ["Light", "Medium", "SemiBold", "Bold", "Heavy"]
FILES = {
    "Light":    "思源宋Light.png",
    "Medium":   "思源宋Medium.png",
    "SemiBold": "思源宋SemiBold.png",
    "Bold":     "思源宋Bold.png",
    "Heavy":    "思源宋heavy.png",
}

MAXV = 255.0          # 像素最大值（8 位图像）
INK_TH = 128          # 判定墨色像素的灰度阈值
DIFF_GAIN = 4         # 差异图放大倍数

# 中文字体（用于图表标注）
zh_fonts = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
avail = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.sans-serif"] = [f for f in zh_fonts if f in avail] + \
                                  plt.rcParams["font.sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


# ----------------------------------------------------------------------
# 1. 读图：RGBA 合成到白底后转灰度 / RGB 张量
# ----------------------------------------------------------------------
def load_gray(path):
    """读图并合成到白色背景，返回 float64 灰度数组，范围 [0,255]。"""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return np.asarray(im.convert("L"), dtype=np.float64)


def load_rgb_tensor(path):
    """读图并合成到白色背景，返回 (1,3,H,W) 张量，范围 [-1,1]（LPIPS 输入）。"""
    im = Image.open(path)
    if im.mode == "RGBA":
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return t * 2.0 - 1.0


grays = {w: load_gray(os.path.join(BASE, FILES[w])) for w in WEIGHTS}
rgbs = {w: load_rgb_tensor(os.path.join(BASE, FILES[w])) for w in WEIGHTS}

sizes = {g.shape for g in grays.values()}
assert len(sizes) == 1, f"图像尺寸不一致: {sizes}"
H, W = sizes.pop()
print(f"图像尺寸: {W}x{H}，共 {len(WEIGHTS)} 个字重\n")

# ----------------------------------------------------------------------
# 2. 单图统计：墨色像素占比、平均灰度
# ----------------------------------------------------------------------
stat_rows = []
for w in WEIGHTS:
    g = grays[w]
    stat_rows.append({
        "字重": w,
        "墨色像素占比(灰度<128)": round(float((g < INK_TH).mean()), 6),
        "平均灰度": round(float(g.mean()), 3),
    })
df_stat = pd.DataFrame(stat_rows)
df_stat.to_csv(os.path.join(OUT, "单图统计.csv"), index=False, encoding="utf-8-sig")
print(df_stat.to_string(index=False), "\n")

# ----------------------------------------------------------------------
# 3. 两两计算指标
# ----------------------------------------------------------------------
print("加载 LPIPS (AlexNet) 模型……")
lpips_fn = lpips.LPIPS(net="alex", verbose=False)

rows = []
for a, b in itertools.combinations(WEIGHTS, 2):
    ga, gb = grays[a], grays[b]
    diff = ga - gb

    mae = float(np.abs(diff).mean())
    mse = float((diff ** 2).mean())
    rmse = float(np.sqrt(mse))
    psnr = float("inf") if mse == 0 else float(20.0 * np.log10(MAXV / rmse))
    ssim = float(ssim_fn(ga, gb, data_range=MAXV))
    with torch.no_grad():
        lp = float(lpips_fn(rgbs[a], rgbs[b]).item())

    # 补充：仅在两图墨色像素的并集区域内计算的 MAE（排除大面积白底的影响）
    mask = (ga < 250) | (gb < 250)
    mae_ink = float(np.abs(diff)[mask].mean()) if mask.any() else 0.0

    rows.append({
        "字重A": a, "字重B": b,
        "字重间隔": abs(WEIGHTS.index(a) - WEIGHTS.index(b)),
        "MAE": round(mae, 4), "MSE": round(mse, 4), "RMSE": round(rmse, 4),
        "PSNR(dB)": round(psnr, 4), "SSIM": round(ssim, 6), "LPIPS": round(lp, 6),
        "MAE_墨色区": round(mae_ink, 4),
    })

    # 保存绝对差放大图（白=无差异，黑=差异大）
    dimg = np.clip(np.abs(diff) * DIFF_GAIN, 0, 255).astype(np.uint8)
    Image.fromarray(255 - dimg, mode="L").save(
        os.path.join(DIFF_DIR, f"diff_{a}_vs_{b}.png"))

df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "成对指标.csv"), index=False, encoding="utf-8-sig")
print(df.to_string(index=False), "\n")

# ----------------------------------------------------------------------
# 4. 指标矩阵 + 热力图
# ----------------------------------------------------------------------
METRICS = ["MAE", "MSE", "RMSE", "PSNR(dB)", "SSIM", "LPIPS"]
mats = {}
for m in METRICS:
    M = np.full((len(WEIGHTS), len(WEIGHTS)), np.nan)
    for r in rows:
        i, j = WEIGHTS.index(r["字重A"]), WEIGHTS.index(r["字重B"])
        M[i, j] = M[j, i] = r[m]
    mats[m] = M
    pd.DataFrame(M, index=WEIGHTS, columns=WEIGHTS).to_csv(
        os.path.join(OUT, f"指标矩阵_{m.replace('(dB)', '')}.csv"),
        encoding="utf-8-sig")

for m in METRICS:
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(mats[m], cmap="viridis")
    ax.set_xticks(range(len(WEIGHTS)), WEIGHTS)
    ax.set_yticks(range(len(WEIGHTS)), WEIGHTS)
    for i in range(len(WEIGHTS)):
        for j in range(len(WEIGHTS)):
            if not np.isnan(mats[m][i, j]):
                ax.text(j, i, f"{mats[m][i, j]:.3g}", ha="center", va="center",
                        color="w", fontsize=8)
    ax.set_title(f"各字重两两比较：{m}")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"热力图_{m.replace('(dB)', '')}.png"), dpi=150)
    plt.close(fig)

# ----------------------------------------------------------------------
# 5. 以 Heavy 为基准的指标柱状图
# ----------------------------------------------------------------------
BASE_W = "Heavy"
base = df[(df["字重A"] == BASE_W) | (df["字重B"] == BASE_W)].copy()
base["对比方"] = base.apply(
    lambda r: r["字重A"] if r["字重B"] == BASE_W else r["字重B"], axis=1)
base["_o"] = base["对比方"].map({w: i for i, w in enumerate(WEIGHTS)})
base = base.sort_values("_o")

fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for ax, m in zip(axes.flat, METRICS):
    labels = [f"{r['对比方']}\nvs\n{BASE_W}" for _, r in base.iterrows()]
    ax.bar(labels, base[m], color="#4C72B0")
    ax.set_title(m)
    for k, v in enumerate(base[m]):
        ax.text(k, v, f"{v:.3g}", ha="center", va="bottom", fontsize=8)
fig.suptitle(f"以 {BASE_W} 为基准的字重差异指标")
fig.tight_layout()
fig.savefig(os.path.join(OUT, f"以{BASE_W}为基准指标.png"), dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------
# 6. 字重对比与基准差异图
# ----------------------------------------------------------------------
fig, axes = plt.subplots(2, 5, figsize=(15, 6.5))
for k, w in enumerate(WEIGHTS):
    axes[0, k].imshow(grays[w], cmap="gray", vmin=0, vmax=255)
    tag = "（基准）" if w == BASE_W else ""
    axes[0, k].set_title(
        f"{w}{tag}（墨色 {stat_rows[k]['墨色像素占比(灰度<128)']:.1%}）")
    axes[0, k].axis("off")
others = [w for w in WEIGHTS if w != BASE_W]
for k, w in enumerate(others):   # 差异图放在对应字重的正下方
    dimg = np.clip(np.abs(grays[w] - grays[BASE_W]) * DIFF_GAIN, 0, 255)
    axes[1, k].imshow(dimg, cmap="hot", vmin=0, vmax=255)
    axes[1, k].set_title(f"{w} vs {BASE_W}\n差异x{DIFF_GAIN}")
    axes[1, k].axis("off")
axes[1, len(others)].set_title(f"{BASE_W}（基准）")
axes[1, len(others)].axis("off")
fig.suptitle(f"上排：5 个字重原图　下排：各字重与基准 {BASE_W} 的差异")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "字重对比与差异图.png"), dpi=150)
plt.close(fig)

print(f"全部完成，结果已保存到: {OUT}")
