# -*- coding: utf-8 -*-
"""
实验4（附图）：fontTools.misc.transform 二维几何变换示意图的生成
对应书稿「字形的二维平面上的几何变换」一节的例程（lst:transform2d1）。
本程序分两部分：
  第一部分即书稿例程本体——用 Transform / Identity / Offset / Scale 构造
  仿射变换矩阵，transformPoint / transformPoints 施加到坐标点，inverse()
  求逆；再经 TransformPen 把 4 种基本变换施加到思源宋体 “永” 字的完整
  轮廓上，由 RecordingPen 记录变换后的路径命令（字形原始数据不变）。
  第二部分把各变换结果绘制成 2×3 示意图（各栏共用同一比例，尺寸差异
  即实际变换效果）：
  ① 原字形与字体坐标系（em 方格、基线、原点）；
  ② translate(200, 80)：平移，蓝箭头为位移矢量；
  ③ scale(0.7, 1.25)：非等比缩放，字形变窄长高；
  ④ rotate(π/6)：绕原点逆时针旋转 30°，蓝弧标示旋转方向；
  ⑤ skew(π/9, 0)：X 方向倾斜，各点水平位移与到基线的距离成正比，
     基线保持不动（蓝箭头长度即位移量）；
  ⑥ 复合变换 scale(0.8)·rotate(25°)。
  每栏下方标注该变换矩阵的 6 元组 (xx, xy, yx, yy, dx, dy) 实测值。
输出：transform2d示意图.png（位图）与 transform2d示意图.pdf（矢量图）
"""
import math
from fontTools.misc.transform import Transform, Identity, Offset, Scale
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ========== 第一部分：书稿例程（lst:transform2d1） ==========
# 1) 直接给出 6 个矩阵元素构造变换：(xx, xy, yx, yy, dx, dy)
t = Transform(2, 0, 0, 3, 0, 0)              # x、y 方向分别缩放 2、3 倍
print(t.transformPoint((100, 100)))          # (200, 300)
t = Offset(2, 3)                             # 等价于 Transform(1, 0, 0, 1, 2, 3)
print(t.transformPoint((100, 100)))          # (102, 103)

# 2) 以 Identity 为起点链式复合：translate / scale / rotate / skew
t = Identity.scale(0.5).translate(100, 200).skew(0.1, 0.2)
print([tuple(round(v, 2) for v in p)
       for p in t.transformPoints([(0, 0), (1, 1), (100, 100)])])
# [(50.0, 100.0), (50.55, 100.6), (105.02, 160.14)] —— 后链接的变换先作用于点
print(Identity.rotate(math.pi / 2).transformPoint((100, 100)))   # (-100, 100)
t2 = Identity.translate(2, 3).scale(4, 5)
print(t2.transformPoint((10, 20)), t2.inverse().transformPoint((42, 103)))
# (42, 103) (10.0, 20.0) —— inverse() 求逆变换，把点映射回原处

# 3) 经 TransformPen 施加到整个字形（以思源宋体 “永” 为例）
font = TTFont("SourceHanSerifCN-Regular-1.otf")
glyphSet = font.getGlyphSet()
glyph = glyphSet[font.getBestCmap()[ord('永')]]
rec0 = RecordingPen()
glyph.draw(rec0)
print("原始", rec0.value[0])
TRANSFORMS = [("平移", Identity.translate(200, 80)),
              ("缩放", Identity.scale(0.7, 1.25)),
              ("旋转", Identity.rotate(math.radians(30))),
              ("倾斜", Identity.skew(math.radians(20), 0))]
for name, tr in TRANSFORMS:
    rec = RecordingPen()
    glyph.draw(TransformPen(rec, tr))        # 逐点乘以矩阵后转发记录
    print(name, tuple(round(v, 3) for v in tr), rec.value[0])

# ========== 第二部分：绘制 2×3 示意图 ==========
GRAY, GHOST = '#777777', '#999999'
GHOST_FILL = '#f2f2f2'
BLUE, RED, BLACK = '#0055cc', '#cc2222', 'black'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]


def record(transform=None):
    """把字形轮廓记录为路径命令；给定 transform 时经 TransformPen 实时变换"""
    rec = RecordingPen()
    if transform is None:
        glyph.draw(rec)
    else:
        glyph.draw(TransformPen(rec, transform))
    return rec.value


def cmds_to_verts(commands):
    """路径命令 → (顶点数组, 路径码)，供 matplotlib Path 使用"""
    verts, codes = [], []
    for cmd, pts in commands:
        if cmd == "moveTo":
            codes.append(Path.MOVETO)
            verts.append(pts[0])
        elif cmd == "lineTo":
            codes.append(Path.LINETO)
            verts.append(pts[0])
        elif cmd == "curveTo":               # 三次贝塞尔（CFF 轮廓）
            codes += [Path.CURVE4, Path.CURVE4, Path.CURVE4]
            verts += list(pts)
        elif cmd == "qCurveTo":              # 二次贝塞尔（TrueType 轮廓）
            pts = list(pts)
            for i in range(len(pts) - 1):
                codes += [Path.CURVE3, Path.CURVE3]
                verts += [pts[i], pts[i + 1]]
        elif cmd == "closePath":
            codes.append(Path.CLOSEPOLY)
            verts.append((0, 0))
    return np.array(verts, dtype=float), codes


def fmt6(tr):
    """把 6 元组格式化为紧凑字符串，整数不写小数点"""
    def f(v):
        v = round(float(v), 3)
        return str(int(v)) if v == int(v) else str(v)
    return f"({f(tr[0])}, {f(tr[1])}, {f(tr[2])}, {f(tr[3])}, {f(tr[4])}, {f(tr[5])})"


# 原始字形与各变体的路径
raw = record()
verts0, codes = cmds_to_verts(raw)
COMPOSITE = Identity.scale(0.8).rotate(math.radians(25))
variants = {name: cmds_to_verts(record(tr))[0] for name, tr in TRANSFORMS}
verts6, _ = cmds_to_verts(record(COMPOSITE))

# 统一比例：所有变体中最大的外接框边长占 250 图单位
def bbox(v):
    return v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max()

extents = [bbox(v) for v in list(variants.values()) + [verts0, verts6]]
max_side = max(max(x1 - x0, y1 - y0) for x0, y0, x1, y1 in extents)
S = 250.0 / max_side
print(f"统一比例 S = {S:.4f}（最大边长 {max_side:.0f} 字体单位 → 250 图单位）")

# 画布：2 行 3 列，坐标区充满整幅
W, H = 1380, 830
fig = plt.figure(figsize=(13.8, 8.3))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect('equal')
ax.axis('off')

COLS = [230, 690, 1150]                    # 三列中心
ROW_CY = [555, 170]                        # 两行字形中心高度
ROW_TITLE = [760, 368]                     # 两行标题高度
ROW_TUPLE = [405, 28]                      # 两行矩阵标注高度

CX0, CY0 = 501.5, 379.5                    # 原始字形外接框中心（字体坐标）


def place_centered(verts, cx, cy, extra_dx=0.0, extra_dy=0.0):
    """按外接框中心对齐到 (cx, cy)，缩放 S，可附加位移（图单位）"""
    x0, y0, x1, y1 = bbox(verts)
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    return (verts - c) * S + np.array([cx + extra_dx, cy + extra_dy])


def draw_glyph(verts, cx, cy, fill, edge, lw=1.0, ls='-', z=3,
               extra_dx=0.0, extra_dy=0.0):
    v = place_centered(verts, cx, cy, extra_dx, extra_dy)
    ax.add_patch(PathPatch(Path(v, codes), facecolor=fill, edgecolor=edge,
                           linewidth=lw, linestyle=ls, zorder=z))
    return v


def panel_title(col, row, text):
    ax.text(col, ROW_TITLE[row], text, ha='center', va='center',
            fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)


def panel_tuple(col, row, text, color='#333333'):
    ax.text(col, ROW_TUPLE[row], text, ha='center', va='center',
            fontsize=10.5, family='monospace', color=color,
            path_effects=WHITE_STROKE)


def draw_ghost(cx, cy):
    draw_glyph(verts0, cx, cy, GHOST_FILL, GHOST, lw=1.0,
               ls=(0, (4, 2.5)), z=2)


# ---------- ① 原字形与字体坐标系 ----------
cx, cy = COLS[0], ROW_CY[0]
panel_title(cx, 0, "① 原字形与字体坐标系")
ox, oy = cx - 500 * S, cy - 500 * S        # 原点 (0,0) 的图坐标：em 方格居中
ax.add_patch(plt.Rectangle((ox, oy), 1000 * S, 1000 * S,
                           facecolor='none', edgecolor=GHOST, lw=1.0,
                           linestyle=(0, (4, 2.5)), zorder=1))
ax.text(ox + 1000 * S, oy + 1000 * S + 12, "em 方格 1000×1000",
        ha='right', va='bottom', fontsize=9.5, color=GRAY)
# 基线（x 轴）与 y 轴
ax.plot([ox - 18, ox + 1000 * S + 18], [oy, oy], color=GRAY, lw=1.0, zorder=1)
ax.plot([ox, ox], [oy - 18, oy + 1000 * S + 18], color=GRAY, lw=1.0, zorder=1)
ax.text(ox + 1000 * S + 22, oy, "基线 y = 0", ha='left', va='center',
        fontsize=9.5, color=GRAY)
ax.plot([ox], [oy], 'o', ms=4, color=BLACK, zorder=4)
ax.text(ox - 8, oy - 16, "(0, 0)", ha='right', va='top', fontsize=9.5,
        color=BLACK)
v = verts0 * S + np.array([ox, oy])
ax.add_patch(PathPatch(Path(v, codes), facecolor=BLACK, edgecolor='none',
                       zorder=3))
panel_tuple(cx, 0, "(xx, xy, yx, yy, dx, dy)")

# ---------- ② translate(200, 80)：平移 ----------
cx, cy = COLS[1], ROW_CY[0]
panel_title(cx, 0, "② translate(200, 80)：平移")
draw_ghost(cx, cy)
dxp, dyp = 200 * S, 80 * S                 # 位移矢量的图坐标分量
draw_glyph(variants["平移"], cx, cy, BLACK, 'none', extra_dx=dxp,
           extra_dy=dyp)
# 位移矢量画在字形上方，避免被笔画遮盖
y_vec = cy + 128
for lw_, c_, ms_ in [(4.5, 'white', 22), (1.8, BLUE, 16)]:
    ax.annotate('', xy=(cx + dxp / 2, y_vec + dyp),
                xytext=(cx - dxp / 2, y_vec),
                arrowprops=dict(arrowstyle='-|>', lw=lw_, color=c_,
                                mutation_scale=ms_), zorder=5)
ax.text(cx, y_vec + dyp + 14, "(dx, dy) = (200, 80)", ha='center',
        va='bottom', fontsize=10, color=BLUE, path_effects=WHITE_STROKE)
panel_tuple(cx, 0, fmt6(TRANSFORMS[0][1]))

# ---------- ③ scale(0.7, 1.25)：缩放 ----------
cx, cy = COLS[2], ROW_CY[0]
panel_title(cx, 0, "③ scale(0.7, 1.25)：缩放")
draw_ghost(cx, cy)
draw_glyph(variants["缩放"], cx, cy, BLACK, 'none')
panel_tuple(cx, 0, fmt6(TRANSFORMS[1][1]))

# ---------- ④ rotate(π/6)：旋转 30° ----------
cx, cy = COLS[0], ROW_CY[1]
panel_title(cx, 1, "④ rotate(π/6)：旋转 30°")
draw_ghost(cx, cy)
draw_glyph(variants["旋转"], cx, cy, BLACK, 'none')
r_arc = 140
ang = np.linspace(0, 30, 30) * np.pi / 180
arc = np.array([cx, cy])[:, None] + r_arc * np.vstack([np.cos(ang),
                                                       np.sin(ang)])
ax.plot(arc[0], arc[1], color='white', lw=4.5, zorder=4)
ax.plot(arc[0], arc[1], color=BLUE, lw=1.6, zorder=5)
ax.annotate('', xy=(arc[0, -1], arc[1, -1]),
            xytext=(arc[0, -3], arc[1, -3]),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14), zorder=5)
lbl = np.array([cx, cy]) + (r_arc + 18) * np.array([np.cos(15 * np.pi / 180),
                                                    np.sin(15 * np.pi / 180)])
ax.text(*lbl, "30°", ha='center', va='center', fontsize=10.5, color=BLUE,
        path_effects=WHITE_STROKE)
panel_tuple(cx, 1, fmt6(TRANSFORMS[2][1]))

# ---------- ⑤ skew(π/9, 0)：倾斜 ----------
cx, cy = COLS[1], ROW_CY[1]
panel_title(cx, 1, "⑤ skew(π/9, 0)：倾斜")
draw_ghost(cx, cy)
draw_glyph(variants["倾斜"], cx, cy, BLACK, 'none')
y_base = cy - CY0 * S                      # 基线（y=0）的图坐标
ax.plot([cx - 150, cx + 165], [y_base, y_base], color=GHOST, lw=1.0,
        linestyle=(0, (4, 2.5)), zorder=1)
ax.text(cx + 170, y_base, "基线 y = 0（不动）", ha='left', va='center',
        fontsize=9, color=GRAY)
tan20 = math.tan(math.radians(20))
for yf in [300, 600, 835]:                 # 三个字体高度处的位移箭头
    yp = cy + (yf - CY0) * S
    dxp = tan20 * yf * S                   # 位移量 Δx = tan(α)·y
    for lw_, c_, ms_ in [(4.0, 'white', 16), (1.5, BLUE, 11)]:
        ax.annotate('', xy=(cx + 108 + dxp, yp), xytext=(cx + 108, yp),
                    arrowprops=dict(arrowstyle='-|>', lw=lw_, color=c_,
                                    mutation_scale=ms_), zorder=5)
ax.text(cx + 108 + tan20 * 835 * S + 8, cy + (835 - CY0) * S,
        "Δx = tan(α)·y", ha='left', va='center', fontsize=10, color=BLUE,
        path_effects=WHITE_STROKE)
panel_tuple(cx, 1, fmt6(TRANSFORMS[3][1]))

# ---------- ⑥ 复合变换 scale(0.8)·rotate(25°) ----------
cx, cy = COLS[2], ROW_CY[1]
panel_title(cx, 1, "⑥ 复合 scale(0.8)·rotate(25°)")
draw_ghost(cx, cy)
draw_glyph(verts6, cx, cy, BLACK, 'none')
ax.text(cx, ROW_TUPLE[1] + 24, "Identity.scale(0.8).rotate(radians(25))",
        ha='center', va='center', fontsize=8.5, family='monospace',
        color=GRAY, path_effects=WHITE_STROKE)
panel_tuple(cx, 1, fmt6(COMPOSITE))

# ---------- 输出 ----------
fig.savefig('transform2d示意图.png', dpi=200)
fig.savefig('transform2d示意图.pdf')
print('已生成 transform2d示意图.png 与 transform2d示意图.pdf')
