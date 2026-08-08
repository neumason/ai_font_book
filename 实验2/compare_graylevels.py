# -*- coding: utf-8 -*-
"""
实验2：同一汉字同一字重、不同灰度图像的相似度指标比较
====================================================
对思源宋体 Heavy 字重的"永"字 3 个灰度版本
（纯黑 墨色K≈2 / 深灰 K≈52 / 中灰 K≈107）两两计算 6 种指标：

    MAE   平均绝对误差          （越小越相似）
    MSE   均方误差              （越小越相似）
    RMSE  均方根误差            （越小越相似）
    PSNR  峰值信噪比            （越大越相似，单位 dB）
    SSIM  结构相似度            （越大越相似，范围 0~1）
    LPIPS 感知相似度(AlexNet)   （越小越相似）

注意：本组 PNG 为 RGBA，透明背景的 RGB 值为 0，直接 convert("L")
会把背景误读为黑色，必须先按 alpha 通道合成到白底再转灰度。

输出（保存在 结果/ 目录下）：
    单图统计.csv          各版本的墨色像素占比、墨色灰度、平均灰度
    成对指标.csv          3 个图像对的全部指标
    指标矩阵_*.csv        各指标的 3×3 矩阵
    热力图_*.png          各指标的成对热力图
    以原图为基准指标.png  各灰度版本与基准（纯黑原图）的 6 指标柱状图
    灰度对比与差异图.png  3 个版本原图 + 与基准原图的差异放大图
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

# 按墨色灰度由深到浅排列
LEVELS = ["纯黑", "深灰", "中灰"]
FILES = {
    "纯黑": "思源宋heavy.png",
    "深灰": "思源宋heavy-灰度1.png",
    "中灰": "思源宋heavy-灰度2.png",
}

MAXV = 255.0          # 像素最大值（8 位图像）
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


grays = {w: load_gray(os.path.join(BASE, FILES[w])) for w in LEVELS}
rgbs = {w: load_rgb_tensor(os.path.join(BASE, FILES[w])) for w in LEVELS}

sizes = {g.shape for g in grays.values()}
assert len(sizes) == 1, f"图像尺寸不一致: {sizes}"
H, W = sizes.pop()
print(f"图像尺寸: {W}x{H}，共 {len(LEVELS)} 个灰度版本\n")

# ----------------------------------------------------------------------
# 2. 单图统计：墨色像素占比、墨色灰度、平均灰度
# ----------------------------------------------------------------------
stat_rows = []
inkK = {}   # 各版本的墨色代表灰度（中位数）
for w in LEVELS:
    g = grays[w]
    ink = g < 250
    K = float(np.median(g[ink])) if ink.any() else float("nan")
    inkK[w] = K
    stat_rows.append({
        "版本": w,
        "墨色像素占比(灰度<250)": round(float(ink.mean()), 6),
        "墨色灰度K(中位数)": round(K, 1),
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
for a, b in itertools.combinations(LEVELS, 2):
    ga, gb = grays[a], grays[b]
    diff = ga - gb
    dK = abs(inkK[a] - inkK[b])

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
        "版本A": a, "版本B": b,
        "灰度差ΔK": round(dK, 1),
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
    M = np.full((len(LEVELS), len(LEVELS)), np.nan)
    for r in rows:
        i, j = LEVELS.index(r["版本A"]), LEVELS.index(r["版本B"])
        M[i, j] = M[j, i] = r[m]
    mats[m] = M
    pd.DataFrame(M, index=LEVELS, columns=LEVELS).to_csv(
        os.path.join(OUT, f"指标矩阵_{m.replace('(dB)', '')}.csv"),
        encoding="utf-8-sig")

for m in METRICS:
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(mats[m], cmap="viridis")
    ax.set_xticks(range(len(LEVELS)), LEVELS)
    ax.set_yticks(range(len(LEVELS)), LEVELS)
    for i in range(len(LEVELS)):
        for j in range(len(LEVELS)):
            if not np.isnan(mats[m][i, j]):
                ax.text(j, i, f"{mats[m][i, j]:.3g}", ha="center", va="center",
                        color="w", fontsize=9)
    ax.set_title(f"各灰度版本两两比较：{m}")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"热力图_{m.replace('(dB)', '')}.png"), dpi=150)
    plt.close(fig)

# ----------------------------------------------------------------------
# 5. 以纯黑原图为基准的指标柱状图
# ----------------------------------------------------------------------
BASE_L = "纯黑"
base = df[(df["版本A"] == BASE_L) | (df["版本B"] == BASE_L)].copy()
base["对比方"] = base.apply(
    lambda r: r["版本A"] if r["版本B"] == BASE_L else r["版本B"], axis=1)
base["_o"] = base["对比方"].map({w: i for i, w in enumerate(LEVELS)})
base = base.sort_values("_o")

fig, axes = plt.subplots(2, 3, figsize=(12, 7))
for ax, m in zip(axes.flat, METRICS):
    labels = [f"{r['对比方']}\nvs\n{BASE_L}（基准）" for _, r in base.iterrows()]
    ax.bar(labels, base[m], color="#4C72B0")
    ax.set_title(m)
    for k, v in enumerate(base[m]):
        ax.text(k, v, f"{v:.3g}", ha="center", va="bottom", fontsize=9)
fig.suptitle(f"以 {BASE_L}（纯黑）为基准的灰度差异指标")
fig.tight_layout()
fig.savefig(os.path.join(OUT, f"以{BASE_L}为基准指标.png"), dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------
# 6. 灰度版本对比与基准差异图
# ----------------------------------------------------------------------
fig, axes = plt.subplots(2, 3, figsize=(10, 7))
for k, w in enumerate(LEVELS):
    axes[0, k].imshow(grays[w], cmap="gray", vmin=0, vmax=255)
    tag = "（基准）" if w == BASE_L else ""
    axes[0, k].set_title(f"{w}{tag}（墨色K≈{inkK[w]:.0f}）")
    axes[0, k].axis("off")
others = [w for w in LEVELS if w != BASE_L]
for k, w in enumerate(others):   # 差异图放在对应版本的正下方
    dimg = np.clip(np.abs(grays[w] - grays[BASE_L]) * DIFF_GAIN, 0, 255)
    axes[1, k + 1].imshow(dimg, cmap="hot", vmin=0, vmax=255)
    axes[1, k + 1].set_title(f"{w} vs {BASE_L}\n差异x{DIFF_GAIN}")
    axes[1, k + 1].axis("off")
axes[1, 0].set_title(f"{BASE_L}（基准）")
axes[1, 0].axis("off")
fig.suptitle(f"上排：3 个灰度版本原图　下排：各版本与基准 {BASE_L} 的差异")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "灰度对比与差异图.png"), dpi=150)
plt.close(fig)

print(f"全部完成，结果已保存到: {OUT}")
