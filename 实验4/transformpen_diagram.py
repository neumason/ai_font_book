# -*- coding: utf-8 -*-
"""
实验4（附图）：TransformPen 字形变换示意图的生成
对应书稿「TransformPen字形变换器」一节的例程（lst:transformpen1）：
    transform = Identity.rotate(0.785398)   # 45°（弧度，逆时针）
    transform = transform.scale(2)          # 再放大 2 倍
    transformPen = TransformPen(roundpen, transform)
TransformPen 把每个点坐标乘以 2×3 仿射矩阵后转发给下游 Pen，路径原始
数据不变；例程中三笔串联：TransformPen → RoundingPen（取整）→
RecordingPen（记录）。本程序真实执行该例程，三栏共用同一比例（尺寸
变化即实际变换效果）：
  ① 原始路径：100×100 正方形，顶点标注原始坐标；
  ② rotate(0.785398)：逆时针旋转 45° 后的菱形（灰虚线为原始正方形，
     蓝箭头标示旋转方向），下方为旋转矩阵；
  ③ scale(2)：再放大 2 倍的最终菱形，顶点坐标为 RecordingPen 实际
     记录值（经 RoundingPen 取整），灰虚线为旋转阶段的轮廓。
输出：transformpen示意图.png（位图）与 transformpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.pens.roundingPen import RoundingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.misc.transform import Identity
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 真实执行书稿例程 ----------
SQUARE = [(50, 50), (150, 50), (150, 150), (50, 150)]   # 例程的正方形
recordingPen = RecordingPen()
roundpen = RoundingPen(recordingPen)
transform = Identity.rotate(0.785398)        # 45°（弧度）
transform = transform.scale(2)               # 再放大 2 倍
transformPen = TransformPen(roundpen, transform)
transformPen.moveTo(SQUARE[0])
for pt in SQUARE[1:]:
    transformPen.lineTo(pt)
transformPen.closePath()
recorded = [pts[0] for cmd, pts in recordingPen.value if cmd != 'closePath']
print("复合矩阵:", transform)
print("RecordingPen 记录:", recordingPen.value)

# 各阶段顶点（rotate 阶段未取整，由矩阵直接计算）
rot_only = Identity.rotate(0.785398)
pts_rot = [rot_only.transformPoint(p) for p in SQUARE]
pts_final = [transform.transformPoint(p) for p in SQUARE]
for p, pr, pf, rc in zip(SQUARE, pts_rot, pts_final, recorded):
    print(f"{p} -> ({pr[0]:.1f}, {pr[1]:.1f}) -> "
          f"({pf[0]:.1f}, {pf[1]:.1f}) -> 取整 {rc}")

# ---------- 2. 画布：21:9 画幅，三栏共用同一比例 ----------
Y0, Y1 = -170, 680                       # 视图纵范围（底部留图例带）
XR = (Y1 - Y0) * 21 / 9                  # 按 21:9 推出横向范围
X0, X1 = -10, -10 + XR
fig = plt.figure(figsize=(12.6, 5.4))    # 12.6 : 5.4 = 21 : 9
ax = fig.add_axes([0, 0, 1, 1])          # 坐标区充满整幅，保证输出严格 21:9
ax.set_xlim(X0, X1)
ax.set_ylim(Y0, Y1)
ax.set_aspect('equal')
ax.axis('off')

BLACK, GRAY = 'black', '#777777'
BLUE, RED = '#0055cc', '#cc2222'
FILL, GHOST = '#dcebfb', '#999999'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]

# 统一比例：最大的最终菱形（对角线 283）占 400 图单位
S = 400 / max(np.linalg.norm(np.array(pts_final[2]) -
                             np.array(pts_final[0])),
              100 * 2 ** 0.5)            # = 400 / 282.84
CY = 380                                 # 各栏形心高度


def centroid(pts):
    return np.mean(np.array(pts), axis=0)


def place(pts, cx):
    """把一组点按形心平移到 (cx, CY) 并缩放 S"""
    c = centroid(pts)
    return [((p[0] - c[0]) * S + cx, (p[1] - c[1]) * S + CY) for p in pts]


def draw_poly(pts, cx, fill, edge, lw=2.2, ls='-', z=3):
    P = place(list(pts) + [pts[0]], cx)
    xs, ys = zip(*P)
    if fill:
        ax.fill(xs, ys, color=fill, zorder=z - 1)
    ax.plot(xs, ys, color=edge, linewidth=lw, linestyle=ls, zorder=z)


# ---------- 3. ① 原始路径 ----------
CX1 = 300
ax.text(CX1, 608, "① 原始路径", ha='center', va='bottom', fontsize=13.5,
        fontweight='bold', path_effects=WHITE_STROKE)
draw_poly(SQUARE, CX1, FILL, BLACK)
LBL1 = [(-14, -14, 'right', 'top'), (14, -14, 'left', 'top'),
        (14, 14, 'left', 'bottom'), (-14, 14, 'right', 'bottom')]
for p, orig, (dx, dy, ha, va) in zip(place(SQUARE, CX1), SQUARE, LBL1):
    ax.plot(*p, 'o', ms=4.5, color=BLACK, zorder=4)
    ax.text(p[0] + dx, p[1] + dy, f"({orig[0]}, {orig[1]})", ha=ha, va=va,
            fontsize=10, path_effects=WHITE_STROKE, zorder=5)
ax.text(CX1, 218, "100 × 100 正方形", ha='center', va='top', fontsize=10.5,
        color=GRAY)

# ①→② 箭头
ax.annotate('', xy=(710, 350), xytext=(600, 350),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(655, 385, "rotate(0.785398)", ha='center', va='center',
        fontsize=11, color='#333333', path_effects=WHITE_STROKE)

# ---------- 4. ② rotate(0.785398)：旋转 45° ----------
CX2 = 972
ax.text(CX2, 608, "② rotate(0.785398)：旋转 45°", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_poly(SQUARE, CX2, None, GHOST, lw=1.2, ls=(0, (4, 2.5)), z=2)
draw_poly(pts_rot, CX2, FILL, BLACK)
for p in place(pts_rot, CX2):
    ax.plot(*p, 'o', ms=4.5, color=BLACK, zorder=4)
# 旋转方向弧（顶点 (50,50) 的轨迹，绕形心示意）
c = np.array([CX2, CY])
r = 130
ang = np.linspace(-135, -90, 40) * np.pi / 180
arc = c[:, None] + r * np.vstack([np.cos(ang), np.sin(ang)])
ax.plot(arc[0], arc[1], color=BLUE, linewidth=1.6, zorder=5)
ax.annotate('', xy=(arc[0, -1], arc[1, -1]),
            xytext=(arc[0, -3], arc[1, -3]),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14), zorder=5)
lbl = c + 152 * np.array([np.cos(-112.5 * np.pi / 180),
                          np.sin(-112.5 * np.pi / 180)])
ax.text(*lbl, "45°", ha='center', va='center', fontsize=11, color=BLUE,
        path_effects=WHITE_STROKE)
# 旋转矩阵
ax.text(CX2, 196, "x' = 0.707x - 0.707y", ha='center', va='center',
        fontsize=10.5, family='monospace', path_effects=WHITE_STROKE)
ax.text(CX2, 160, "y' = 0.707x + 0.707y", ha='center', va='center',
        fontsize=10.5, family='monospace', path_effects=WHITE_STROKE)

# ②→③ 箭头
ax.annotate('', xy=(1250, 350), xytext=(1140, 350),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(1195, 385, "scale(2)", ha='center', va='center', fontsize=11,
        color='#333333', path_effects=WHITE_STROKE)

# ---------- 5. ③ scale(2)：放大 2 倍，RecordingPen 记录 ----------
CX3 = 1650
ax.text(CX3, 608, "③ scale(2)：放大 2 倍", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
draw_poly(pts_rot, CX3, None, GHOST, lw=1.2, ls=(0, (4, 2.5)), z=2)
draw_poly(pts_final, CX3, FILL, BLACK)
LBL3 = [(0, -18, 'center', 'top'), (16, 0, 'left', 'center'),
        (0, -16, 'center', 'top'), (-16, 0, 'right', 'center')]
for p, rc, (dx, dy, ha, va) in zip(place(pts_final, CX3), recorded, LBL3):
    ax.plot(*p, 'o', ms=4.5, color=BLACK, zorder=4)
    ax.text(p[0] + dx, p[1] + dy, f"({rc[0]}, {rc[1]})", ha=ha, va=va,
            fontsize=10, color=RED, path_effects=WHITE_STROKE, zorder=5)
# 复合矩阵
ax.text(CX3, 96, "x' = 1.414x - 1.414y", ha='center', va='center',
        fontsize=10.5, family='monospace', path_effects=WHITE_STROKE)
ax.text(CX3, 60, "y' = 1.414x + 1.414y", ha='center', va='center',
        fontsize=10.5, family='monospace', path_effects=WHITE_STROKE)

# ---------- 6. 底部图例带 ----------
ly1, ly2 = -85, -140
ax.add_patch(plt.Rectangle((6, ly1 - 10), 28, 20, fc=FILL, ec=BLACK,
                           lw=1.2))
ax.text(48, ly1, '各阶段路径（三栏共用同一比例）', va='center', fontsize=11)
ax.plot([420, 448], [ly1, ly1], color=GHOST, linestyle=(0, (4, 2.5)),
        linewidth=1.2)
ax.text(462, ly1, '上一阶段轮廓', va='center', fontsize=11)
ax.annotate('', xy=(770, ly1), xytext=(740, ly1),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14))
ax.text(784, ly1, '旋转方向（逆时针）', va='center', fontsize=11)
ax.plot(1080, ly1, 'o', ms=4.5, color=BLACK)
ax.text(1096, ly1, '路径顶点（③ 中红字为 RecordingPen 实测记录值）',
        va='center', fontsize=11)
ax.text(20, ly2, '笔的串联：TransformPen（施加矩阵） → RoundingPen'
        '（坐标取整） → RecordingPen（记录结果）', va='center',
        fontsize=11, color='#444444')

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('transformpen示意图.png', dpi=200)
fig.savefig('transformpen示意图.pdf')
print('已生成 transformpen示意图.png 与 transformpen示意图.pdf（21:9）')
