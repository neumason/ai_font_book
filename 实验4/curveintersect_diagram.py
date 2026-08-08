# -*- coding: utf-8 -*-
"""
实验4（附图）：曲线交点计算示意图的生成
对应书稿「曲线交点计算」一节的例程（lst:curveintersect1）：
    intersections1 = curveCurveIntersections(curve1, curve2)
    intersections2 = curveLineIntersections(curve1, line)
两个函数均返回 (pt, t1, t2) 元组的列表：pt 为交点坐标，t1、t2 分别为
交点在第一条、第二条曲线（或直线）上的参数值。以书稿例程的
curve1、curve2 与 line 为例，分三栏可视化求交结果：
  ① curveCurveIntersections：曲线×曲线，3 个交点（绿 ×）及其参数值；
  ② curveLineIntersections：曲线×直线，1 个交点（紫 ●）及其参数值；
  ③ 返回值列表：两个函数实际返回的 (pt, t1, t2) 元组。
所有交点均由 fontTools.misc.bezierTools 真实计算。
输出：curveintersect示意图.png（位图）与 curveintersect示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.misc.bezierTools import curveCurveIntersections, \
    curveLineIntersections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 真实执行书稿例程 ----------
curve1 = [(10, 100), (90, 30), (40, 140), (220, 180)]
curve2 = [(5, 150), (180, 20), (80, 250), (210, 150)]
line = [(25, 260), (230, 20)]
intersections1 = curveCurveIntersections(curve1, curve2)
intersections2 = curveLineIntersections(curve1, line)
print(f"曲线×曲线：{len(intersections1)} 个交点")
for pt, t1, t2 in intersections1:
    print(f"  pt=({pt[0]:.2f}, {pt[1]:.2f})  t1={t1:.4f} t2={t2:.4f}")
print(f"曲线×直线：{len(intersections2)} 个交点")
for pt, t1, t2 in intersections2:
    print(f"  pt=({pt[0]:.2f}, {pt[1]:.2f})  t1={t1:.4f} t2={t2:.4f}")


def cubic_pts(a, b, c, d, n=150):
    """三次贝塞尔曲线采样点"""
    t = np.linspace(0, 1, n)[:, None]
    P = np.array([a, b, c, d])
    return ((1-t)**3) @ P[0:1] + 3*((1-t)**2)*t @ P[1:2] + \
        3*(1-t)*t**2 @ P[2:3] + t**3 @ P[3:4]


# ---------- 2. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
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
BLUE, RED, GREEN, PURPLE = '#0055cc', '#cc2222', '#00883a', '#8e33cc'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]

# 数据范围 x 0..260, y 20..260 → 图区缩放
SC = 1.7


def T_factory(cx, cy=365):
    return lambda p: ((p[0] - 115) * SC + cx, (p[1] - 140) * SC + cy)


def draw_curve(T, pts, color, z=3):
    xy = np.array([T(p) for p in cubic_pts(*pts)])
    ax.plot(xy[:, 0], xy[:, 1], color=color, linewidth=2.2, zorder=z)


def draw_control_polygon(T, pts, color, z=2):
    P = [T(p) for p in pts]
    ax.plot(*zip(*P), color=color, linestyle=(0, (3, 2.5)), linewidth=0.9,
            zorder=z)
    for i, q in enumerate(P):
        if i == 0 or i == len(P) - 1:
            ax.plot(*q, 'o', ms=4, color=color, zorder=z + 2)
        else:
            ax.plot(*q, 'o', ms=4, mfc='white', mec=color, mew=1.1,
                    zorder=z + 2)


# ---------- 3. ① curveCurveIntersections：曲线×曲线 ----------
CX1 = 330
T1 = T_factory(CX1)
ax.text(CX1, 608, "① curveCurveIntersections：曲线 × 曲线", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_control_polygon(T1, curve1, BLUE)
draw_control_polygon(T1, curve2, RED)
draw_curve(T1, curve1, BLUE)
draw_curve(T1, curve2, RED)
ax.text(T1((130, 20))[0], T1((130, 20))[1], "curve1", ha='center',
        va='top', fontsize=11, color=BLUE, path_effects=WHITE_STROKE)
ax.text(T1((210, 150))[0] + 14, T1((210, 150))[1], "curve2", ha='left',
        va='center', fontsize=11, color=RED, path_effects=WHITE_STROKE)
# 3 个交点（绿 ×）：单行标注坐标与参数值，置于两曲线夹角空白处
LBL1 = [(-14, 0, 'right', 'center'),
        (14, -10, 'left', 'top'),
        (14, 0, 'left', 'center')]
for (pt, t1, t2), (dx, dy, ha, va) in zip(intersections1, LBL1):
    q = T1(pt)
    ax.plot(*q, 'x', ms=11, mew=2.6, color=GREEN, zorder=6)
    ax.text(q[0] + dx, q[1] + dy,
            f"({pt[0]:.0f}, {pt[1]:.0f})  t1={t1:.2f} t2={t2:.2f}",
            ha=ha, va=va, fontsize=9.5, color=GREEN, fontweight='bold',
            path_effects=WHITE_STROKE, zorder=6)

# ---------- 4. ② curveLineIntersections：曲线×直线 ----------
CX2 = 950
T2 = T_factory(CX2)
ax.text(CX2, 608, "② curveLineIntersections：曲线 × 直线", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_control_polygon(T2, curve1, BLUE)
draw_curve(T2, curve1, BLUE)
ax.plot(*zip(T2(line[0]), T2(line[1])), color=GRAY, linewidth=1.8,
        zorder=3)
ax.plot(*T2(line[0]), 'o', ms=4, color=GRAY, zorder=4)
ax.plot(*T2(line[1]), 'o', ms=4, color=GRAY, zorder=4)
ax.text(T2((130, 20))[0], T2((130, 20))[1], "curve1", ha='center',
        va='top', fontsize=11, color=BLUE, path_effects=WHITE_STROKE)
ax.text(T2((230, 20))[0] + 8, T2((230, 20))[1] + 16, "line", ha='left',
        va='bottom', fontsize=11, color=GRAY, path_effects=WHITE_STROKE)
# 1 个交点（紫 ●）：单行标注坐标与参数值
for pt, t1, t2 in intersections2:
    q = T2(pt)
    ax.plot(*q, 'o', ms=10, mfc='white', mec=PURPLE, mew=2.4, zorder=6)
    ax.text(q[0] + 14, q[1], f"({pt[0]:.0f}, {pt[1]:.0f})  "
            f"t1={t1:.2f} t2={t2:.2f}", ha='left', va='center',
            fontsize=9.5, color=PURPLE, fontweight='bold',
            path_effects=WHITE_STROKE, zorder=6)

# ---------- 5. ③ 返回值列表 ----------
CX3 = 1620
ax.text(CX3, 608, "③ 返回值：(pt, t1, t2) 元组", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
frame = FancyBboxPatch((1300, 15), 650, 530, boxstyle="round,pad=10",
                       fc='#f8f8f8', ec='#cccccc', lw=1, zorder=0)
ax.add_patch(frame)
ax.text(1322, 505, "curveCurveIntersections(curve1, curve2)", ha='left',
        va='center', fontsize=10, family='monospace', color=BLACK,
        zorder=3)
for i, (pt, t1, t2) in enumerate(intersections1):
    ax.text(1346, 461 - i * 36,
            f"(({pt[0]:.2f}, {pt[1]:.2f}), t1={t1:.4f}, t2={t2:.4f})",
            ha='left', va='center', fontsize=9.5, family='monospace',
            color=GREEN, zorder=3)
ax.text(1322, 461 - 3 * 36 - 28, "curveLineIntersections(curve1, line)",
        ha='left', va='center', fontsize=10, family='monospace',
        color=BLACK, zorder=3)
for i, (pt, t1, t2) in enumerate(intersections2):
    ax.text(1346, 461 - 4 * 36 - 28,
            f"(({pt[0]:.2f}, {pt[1]:.2f}), t1={t1:.4f}, t2={t2:.4f})",
            ha='left', va='center', fontsize=9.5, family='monospace',
            color=PURPLE, zorder=3)
ax.text(1322, 190, "pt：交点坐标", ha='left', va='center', fontsize=10.5,
        color=GRAY, zorder=3)
ax.text(1322, 154, "t1：交点在 curve1 上的参数值", ha='left', va='center',
        fontsize=10.5, color=GRAY, zorder=3)
ax.text(1322, 118, "t2：交点在 curve2 / line 上的参数值", ha='left',
        va='center', fontsize=10.5, color=GRAY, zorder=3)
ax.text(1322, 66, "配合 cubicPointAtT(*curve, t) 可由参数值", ha='left',
        va='center', fontsize=10.5, color=GRAY, zorder=3)
ax.text(1322, 30, "反查曲线上对应点的坐标", ha='left', va='center',
        fontsize=10.5, color=GRAY, zorder=3)

# ---------- 6. 底部图例带 ----------
ly1 = -85
ax.plot([6, 34], [ly1, ly1], color=BLUE, linewidth=2.2)
ax.text(48, ly1, 'curve1', va='center', fontsize=11)
ax.plot([220, 248], [ly1, ly1], color=RED, linewidth=2.2)
ax.text(262, ly1, 'curve2', va='center', fontsize=11)
ax.plot([420, 448], [ly1, ly1], color=GRAY, linewidth=1.8)
ax.text(462, ly1, 'line', va='center', fontsize=11)
ax.plot(600, ly1, 'x', ms=10, mew=2.4, color=GREEN)
ax.text(616, ly1, '曲线×曲线交点', va='center', fontsize=11)
ax.plot(880, ly1, 'o', ms=9, mfc='white', mec=PURPLE, mew=2.2)
ax.text(898, ly1, '曲线×直线交点', va='center', fontsize=11)
ax.plot([1140, 1168], [ly1, ly1], color=BLUE, linestyle=(0, (3, 2.5)),
        linewidth=0.9)
ax.text(1182, ly1, '控制多边形', va='center', fontsize=11)
ax.text(1420, ly1, '交点标注：坐标与参数值 (t1, t2)', va='center',
        fontsize=11)

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('curveintersect示意图.png', dpi=200)
fig.savefig('curveintersect示意图.pdf')
print('已生成 curveintersect示意图.png 与 curveintersect示意图.pdf（21:9）')
