# 汉字字库书稿配套代码

本书稿（汉字计算机字库设计）配套实验与附图生成代码。涵盖两个方向：

1. **实验 1–3**：以思源宋体「永」字图像为样本，比较不同**字重**、不同**灰度**下图像相似度指标的定量行为（MAE / MSE / RMSE / PSNR / SSIM / LPIPS / FID），并给出可视化结果与复现方法。
2. **实验 4**：书稿各章节（fontTools 字形处理、贝塞尔曲线、笔类 Pen、二维变换等）示例代码的**示意图生成脚本**，输出书中插图。

## 目录结构

```
code/
├── 原始数据/                思源宋体各字重「永」字渲染图、灰度变体、永字原版 PSD
├── 实验1/                  不同字重图像的相似度指标比较
│   ├── compare_weights.py   主脚本（6 指标 × 10 个字重对）
│   ├── 分析报告.md          实验结论与复现方法说明
│   ├── 思源宋*.png          输入图像
│   └── 结果/                指标 CSV、热力图、差异放大图等
├── 实验2/                  同一字重（Heavy）不同灰度图像的相似度指标比较
│   ├── compare_graylevels.py
│   ├── 分析报告.md
│   └── 结果/
├── 实验3/                  不同字重图像的 FID 比较（含小样本噪声地板控制）
│   ├── compute_fid.py
│   ├── 分析报告.md
│   └── 结果/
└── 实验4/                  书稿示意图生成脚本（fontTools / matplotlib）
    ├── baseline_metrics.py  字形的基线计算（OS/2、hhea 表）
    ├── *_diagram.py         各节示意图生成（共 17 个，见下表）
    ├── SourceHanSerifCN-Regular-1.otf   思源宋体（CFF 轮廓示例）
    ├── 思源黑體ExtraLight.ttf           思源黑体（TrueType 轮廓示例）
    └── *.png / *.pdf        已生成的示意图（位图 + 矢量）
```

## 环境依赖

Python ≥ 3.8，主要依赖：

| 包 | 用途 |
|---|---|
| numpy、pandas、Pillow | 图像处理与数据统计 |
| matplotlib | 绘图与示意图 |
| scikit-image | SSIM 计算 |
| torch、torchvision | LPIPS 特征提取（实验1、2）、InceptionV3（实验3） |
| lpips | 感知相似度指标 |
| fontTools | 字体解析与字形处理（实验4） |
| hanzi_chaizi | 汉字拆字（实验4/chaizi_diagram.py） |

安装：

```bash
pip install numpy pandas pillow matplotlib scikit-image torch torchvision lpips fonttools hanzi-chaizi
```

> 实验 1–3 的 LPIPS / FID 均使用预训练模型，首次运行会自动下载权重；无 GPU 时以 CPU 运行即可，只是较慢。

## 实验说明

### 实验 1：不同字重的相似度指标

对思源宋体 5 个字重（Light / Medium / SemiBold / Bold / Heavy）的「永」字对齐图像两两计算 6 种指标，考察**字重梯度**在指标上的反映。

```bash
cd 实验1
python compare_weights.py
```

输出到 `结果/`：单图墨量统计、成对指标表、各指标 5×5 矩阵、热力图、以 Heavy 为基准的柱状图与差异放大图。

**主要结论**：6 种指标排序完全一致；差异由字重间隔主导且近似线性；字重梯度在中间档（Medium~SemiBold）最细腻，Bold 前后跨步最大；结构高度保留，差异集中在笔画轮廓。

### 实验 2：不同灰度的相似度指标

对 Heavy 字重「永」字的 3 个灰度版本（纯黑 / 深灰 / 中灰）两两计算 6 种指标，考察**墨色灰度**而非形状变化时的指标行为。

```bash
cd 实验2
python compare_graylevels.py
```

**主要结论**：指标排序出现分歧（与实验 1 的全面一致相反）；SSIM 在黑端过度敏感；相同 MAE 可对应相差数倍的 MSE/PSNR——比较不同性质差异时，MAE 与 MSE 可能给出相反的相对结论。本实验 RGBA 图像必须先按 alpha 合成到白底再转灰度，直接 `convert("L")` 会把透明背景误读为黑色。

### 实验 3：FID 比较

每个字重仅 1 张图，无法直接构成分布，故采用**图像块（patch）采样**：滑窗提取 128×128 图块（覆盖率 ≥ 2% 的含墨块），缩放至 299×299 后提取 InceptionV3 pool3 特征构成分布。以最粗的 Heavy 为基准计算 FID，并用对半拆分地板与自助法地板控制小样本偏差。

```bash
cd 实验3
python compute_fid.py
```

输出到 `结果/`：FID 基准对比表、5×5 FID 矩阵、噪声地板估计、柱状图、热力图、特征 PCA 散点、图块采样示意。

### 实验 4：书稿示意图

每个脚本对应书稿一节的示例，运行后输出同名 `.png`（位图）与 `.pdf`（矢量图）。**注意：脚本以相对路径读取字体文件，需在 `实验4` 目录内运行。**

| 脚本 | 对应书稿内容 |
|---|---|
| baseline_metrics.py | 字形的基线计算（OS/2、hhea 表） |
| baseline_diagram.py | 基线参考线示意图（h、H、x、g、y、汉） |
| glyph_structure.py | 字符字形的结构信息（glyf 表，以「鹿」为例） |
| bounds_diagram.py | BoundsPen 求取字形边界点 |
| chaizi_diagram.py | 汉字拆字（hanzi_chaizi） |
| pointpen_diagram.py | PointPen 构建自定义字形变换 |
| recordingpen_diagram.py | RecordingPen 捕获字形绘制过程 |
| transformpen_diagram.py | TransformPen 字形变换 |
| ttglyphpen_diagram.py | TTGlyphPen 修改字符曲线 |
| cu2qu_diagram.py | Cu2QuPen 的 TrueType 转换 |
| splitcubic_diagram.py | splitCubicAtT 分割贝塞尔曲线 |
| curveintersect_diagram.py | 曲线交点计算 |
| moments_diagram.py | MomentsPen 求解字形图像 Hu 矩特征 |
| statisticspen_diagram.py | StatisticsPen 字形面积矩统计 |
| svgpathpen_diagram.py | SVGPathPen 字形 SVG 转化 |
| filterpen_diagram.py | filterPen 构建过滤器 |
| filterpen_italic_diagram.py | filterPen 构建斜体过滤器 |
| transform2d_diagram.py | fontTools.misc.transform 二维几何变换 |

示例：

```bash
cd 实验4
python baseline_diagram.py
python moments_diagram.py
```

## 常见问题

- **实验 4 报错找不到字体**：需在 `实验4` 目录下运行（脚本用相对路径加载 `SourceHanSerifCN-Regular-1.otf` 与 `思源黑體ExtraLight.ttf`）。
- **图表中文乱码**：脚本已按「Microsoft YaHei / SimHei / Noto Sans CJK SC」顺序自动选择可用中文字体，Windows 与 macOS 均可直接运行。
- **LPIPS 权重下载失败**：预训练权重从官方源下载，若网络受限可手动配置 `lpips` 的权重缓存路径。

## 许可

- **代码**：以 [MIT License](LICENSE) 授权，Copyright (c) 2026 大连市汉字计算机字库设计技术创新中心。
- **数据与字体文件**（思源宋体、思源黑体、「永」字渲染图等）：版权归原作者所有，不在 MIT 许可范围内。
