# -*- coding: utf-8 -*-
"""
实验4（附图）：字符字形结构信息示意图的生成
对应书稿「字符字形的结构信息」一节的示例：先用 glyf 表读取“鹿”字的
子部件信息（是否组合字形、坐标列表、点标志位、轮廓划分、边界框），
再把这些结构信息直接绘制成示意图。
输出：字形结构示意图.png（位图）与 字形结构示意图.pdf（矢量图）
"""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("思源黑體ExtraLight.ttf")  # 加载思源黑体字库（TrueType 轮廓）
glyphSet = font.getGlyphSet()          # 获取字形集
cmap = font.getBestCmap()              # 最佳字符映射表（Unicode 码点 → 字形名）
glyphName = cmap[ord('鹿')]
glyfTable = font['glyf']               # TrueType 轮廓表
glyph = glyfTable[glyphName]

# ---------- 1. 字形子部件信息（与书稿示例一致） ----------
print(glyph.isComposite())             # 获取字形是否为组合字形
print(glyph.coordinates)               # 获取字形的坐标 (x, y) 的列表
print(glyph.flags)                     # 每个点的标志位
print(glyph.numberOfContours, len(glyph.endPtsOfContours))  # 字形的轮廓数量
print(glyph.endPtsOfContours)          # 每个轮廓的结束点索引
print("Original bounds:", glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax)  # 原始边界框

coords = list(glyph.coordinates)       # 全部点的 (x, y) 坐标
flags = glyph.flags                    # 标志位：bit0 = 1 为曲线上点，0 为控制点
ends = list(glyph.endPtsOfContours)    # 各轮廓结束点的索引
starts = [0] + [e + 1 for e in ends[:-1]]      # 各轮廓起始点的索引
n_on = sum(1 for f in flags if f & 1)  # 曲线上点数
xMin, yMin, xMax, yMax = glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax
width = font['hmtx'][glyphName][0]     # 字宽（步进宽度）
print(f"总点数 {len(coords)}：曲线上点 {n_on}（flag=1）＋ 控制点 {len(flags) - n_on}（flag=0）")


def glyph_path(g):
    """把一个字形轮廓转成 matplotlib 的 Path 对象（字体坐标，基线为 y=0）"""
    pen = RecordingPen()
    g.draw(pen)
    verts, codes = [], []
    for cmd, pts in pen.value:
        if cmd == "moveTo":
            codes.append(Path.MOVETO)
            verts.append(pts[0])
        elif cmd == "lineTo":
            codes.append(Path.LINETO)
            verts.append(pts[0])
        elif cmd == "curveTo":          # 三次贝塞尔（CFF 轮廓）
            codes += [Path.CURVE4, Path.CURVE4, Path.CURVE4]
            verts += list(pts)
        elif cmd == "qCurveTo":         # 二次贝塞尔（TrueType 轮廓）
            pts = list(pts)
            for i in range(len(pts) - 1):
                codes += [Path.CURVE3, Path.CURVE3]
                verts += [pts[i], pts[i + 1]]
        elif cmd == "closePath":
            codes.append(Path.CLOSEPOLY)
            verts.append((0, 0))
    return Path(verts, codes)


# ---------- 2. 绘制字形轮廓与边界框 ----------
fig, ax = plt.subplots(figsize=(11, 5.5))
BLACK = 'black'      # 说明文字与线条统一用黑色
BLUE, RED = '#0055cc', '#cc2222'   # 锚点（曲线上点）用蓝色，轮廓结束点用红色

path = glyph_path(glyphSet[glyphName])
ax.add_patch(PathPatch(path, facecolor='#e8e8e8', edgecolor='black',
                       linewidth=1.2, zorder=1))

# 边界框（虚线）及四边标注
ax.add_patch(Rectangle((xMin, yMin), xMax - xMin, yMax - yMin,
                       fill=False, edgecolor=BLACK, linestyle='--',
                       linewidth=1.0, zorder=2))
cx, cy = (xMin + xMax) / 2, (yMin + yMax) / 2     # 边界框中心
ax.text(cx, yMax + 22, f'yMax = {yMax}', ha='center', va='bottom',
        fontsize=11, color=BLACK)
ax.text(cx, yMin - 22, f'yMin = {yMin}', ha='center', va='top',
        fontsize=11, color=BLACK)
ax.text(xMin - 85, cy, f'xMin = {xMin}', ha='right', va='center',
        rotation=90, fontsize=11, color=BLACK)
ax.text(xMax + 18, cy, f'xMax = {xMax}', ha='left', va='center',
        rotation=90, fontsize=11, color=BLACK)

# 基线、原点位线与字宽线
ax.plot([-120, 1010], [0, 0], color='black', linestyle=(0, (12, 4)),
        linewidth=1.0, zorder=3)                  # 基线 y=0
ax.plot([0, 0], [-260, 900], color=BLACK, linewidth=0.8, zorder=3)
ax.plot([width, width], [-260, 900], color=BLACK, linestyle=':',
        linewidth=0.8, zorder=3)
ax.text(-12, 880, 'x = 0', ha='right', va='top', rotation=90,
        fontsize=10, color=BLACK)
ax.text(width + 12, 880, f'x = {width}', ha='left', va='top', rotation=90,
        fontsize=10, color=BLACK)

# 底部双向箭头：字宽以原点起算
ax.annotate('', xy=(width, -150), xytext=(0, -150),
            arrowprops=dict(arrowstyle='<->', color=BLACK, lw=1.0))
ax.text(width / 2, -185, f'字宽 advance width = {width}',
        ha='center', va='top', fontsize=11, color=BLACK)

# ---------- 3. 绘制点序列：曲线上点、控制点、轮廓划分 ----------
# 控制多边形：点序列中凡涉及控制点的边用点线连出，
# 借以说明二次贝塞尔控制点如何“牵引”曲线
for s, e in zip(starts, ends):
    n = e - s + 1
    for i in range(n):
        j = s + (i + 1) % n
        if not (flags[s + i] & 1 and flags[j] & 1):   # 至少一端是控制点
            (x1, y1), (x2, y2) = coords[s + i], coords[j]
            ax.plot([x1, x2], [y1, y2], ':', color=BLACK, linewidth=0.7,
                    zorder=2)

on_x = [coords[i][0] for i in range(len(coords)) if flags[i] & 1]
on_y = [coords[i][1] for i in range(len(coords)) if flags[i] & 1]
off_x = [coords[i][0] for i in range(len(coords)) if not (flags[i] & 1)]
off_y = [coords[i][1] for i in range(len(coords)) if not (flags[i] & 1)]
ax.scatter(on_x, on_y, s=12, c=BLUE, zorder=5)                     # 锚点（曲线上点）
ax.scatter(off_x, off_y, s=20, facecolors='none', edgecolors=BLACK,
           linewidths=1.0, zorder=5)                                 # 控制点

# 轮廓结束点：方块标记并标注点序号（对应 endPtsOfContours）
end_x = [coords[e][0] for e in ends]
end_y = [coords[e][1] for e in ends]
ax.scatter(end_x, end_y, s=42, marker='s', c=RED, zorder=6)
for e in ends:
    dx, dy = coords[e][0] - cx, coords[e][1] - cy
    r = max((dx * dx + dy * dy) ** 0.5, 1)
    ax.text(coords[e][0] + dx / r * 52, coords[e][1] + dy / r * 52,
            str(e), ha='center', va='center', fontsize=9,
            fontweight='bold', color=RED, zorder=7,
            path_effects=[pe.withStroke(linewidth=2.5, foreground='white')])

# 各轮廓起点：Ck 标注（朝向字形内部，避免与结束点序号重叠）
for k, s in enumerate(starts):
    dx, dy = coords[s][0] - cx, coords[s][1] - cy
    r = max((dx * dx + dy * dy) ** 0.5, 1)
    ax.text(coords[s][0] - dx / r * 58, coords[s][1] - dy / r * 58,
            f'C{k}', ha='center', va='center', fontsize=9,
            fontweight='bold', color=BLACK, zorder=7,
            path_effects=[pe.withStroke(linewidth=2.5, foreground='white')])

# ---------- 4. 右侧信息栏：结构信息汇总与图例 ----------
px = 1080            # 信息栏起始横坐标
info = [
    f"字符 '鹿'（U+9E7F）→ 字形 {glyphName}",
    f"组合字形 isComposite() = {glyph.isComposite()}",
    f"点数 {len(coords)} = 曲线上点 {n_on} ＋ 控制点 {len(flags) - n_on}",
    f"轮廓数 numberOfContours = {glyph.numberOfContours}",
    f"endPtsOfContours = {ends}",
    f"边界框 bounds = ({xMin}, {yMin}, {xMax}, {yMax})",
    f"字宽 advance width = {width}",
]
for i, line in enumerate(info):
    ax.text(px, 830 - i * 75, line, ha='left', va='center', fontsize=12)

ax.scatter([px + 12], [280], s=14, c=BLUE, zorder=7)
ax.text(px + 40, 280, '锚点（曲线上点，flag = 1）', ha='left', va='center', fontsize=12)
ax.scatter([px + 12], [205], s=22, facecolors='none', edgecolors=BLACK,
           linewidths=1.0, zorder=7)
ax.text(px + 40, 205, '控制点（flag = 0）', ha='left', va='center', fontsize=12)
ax.scatter([px + 12], [130], s=30, marker='s', c=RED, zorder=7)
ax.text(px + 40, 130, '轮廓结束点（标注其点序号）', ha='left', va='center',
        fontsize=12)
ax.text(px, 55, 'Ck', ha='left', va='center', fontsize=9,
        fontweight='bold', color=BLACK)
ax.text(px + 50, 55, '第 k 条轮廓的起点', ha='left', va='center', fontsize=12)
ax.plot([px, px + 30], [-20, -20], color='black', linestyle=(0, (12, 4)),
        linewidth=1.0)
ax.text(px + 40, -20, '基线 Baseline（y = 0）', ha='left', va='center',
        fontsize=12)

# ---------- 5. 坐标与输出 ----------
ax.set_xlim(-180, 2450)
ax.set_ylim(-290, 1000)
ax.set_aspect('equal')
ax.axis('off')
fig.savefig('字形结构示意图.png', dpi=200, bbox_inches='tight')
fig.savefig('字形结构示意图.pdf', bbox_inches='tight')
print('已生成 字形结构示意图.png 与 字形结构示意图.pdf')
