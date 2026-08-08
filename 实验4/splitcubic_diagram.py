# -*- coding: utf-8 -*-
"""
实验4（附图）：splitCubicAtT 分割贝塞尔曲线示意图的生成
对应书稿「分割贝塞尔曲线」一节的例程（lst:splitcubic1）：
    curves = splitCubicAtT(p0, p1, p2, p3, 0.3)
splitCubicAtT 按 de Casteljau 算法把三次贝塞尔曲线在参数 t 处分割为
两条子曲线：在控制多边形各边上按比例 t 逐级插值，最后一级插值点即
曲线上的分割点，而各级插值点正好组成两条子曲线的全部控制点。
以书稿例程的曲线 p0=(0,0), p1=(0.5,1.5), p2=(1.5,1.5), p3=(2,0)、
t = 0.3 为例，分三栏可视化分割过程：
  ① 原始曲线：控制多边形与 t = 0.3 处的分割点 S；
  ② de Casteljau 构造：第一级插值点 L0/L1/L2（蓝）、第二级插值点
     M0/M1（绿）、最终分割点 S（红）；
  ③ 分割结果：子曲线 1（红）= (p0, L0, M0, S)，子曲线 2（绿）
     = (S, M1, L2, p3)，灰虚线为原始曲线；两段弧长之和等于原曲线
     弧长（数值为 calcCubicArcLength 实测）。
输出：splitcubic示意图.png（位图）与 splitcubic示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.misc.bezierTools import splitCubicAtT, calcCubicArcLength
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 真实执行书稿例程 ----------
p0, p1, p2, p3 = (0, 0), (0.5, 1.5), (1.5, 1.5), (2, 0)
T_SPLIT = 0.3
curve1, curve2 = splitCubicAtT(p0, p1, p2, p3, T_SPLIT)
len0 = calcCubicArcLength(p0, p1, p2, p3)
len1 = calcCubicArcLength(*curve1)
len2 = calcCubicArcLength(*curve2)
print(f"子曲线 1: {[tuple(round(v, 4) for v in p) for p in curve1]}")
print(f"子曲线 2: {[tuple(round(v, 4) for v in p) for p in curve2]}")
print(f"弧长: 原={len0:.4f} 段1={len1:.4f} 段2={len2:.4f} "
      f"和={len1 + len2:.4f}")


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


# de Casteljau 各级插值点（t = 0.3）
L0, L1, L2 = lerp(p0, p1, T_SPLIT), lerp(p1, p2, T_SPLIT), \
    lerp(p2, p3, T_SPLIT)
M0, M1 = lerp(L0, L1, T_SPLIT), lerp(L1, L2, T_SPLIT)
S_PT = lerp(M0, M1, T_SPLIT)                 # 曲线上的分割点
assert np.allclose(S_PT, curve1[3]) and np.allclose(curve1[1], L0) \
    and np.allclose(curve1[2], M0) and np.allclose(curve2[1], M1) \
    and np.allclose(curve2[2], L2)
print("de Casteljau 插值点即子曲线控制点：L0,L1,L2 =", L0, L1, L2,
      " M0,M1 =", M0, M1, " S =", tuple(round(v, 4) for v in S_PT))


def cubic_pts(a, b, c, d, n=120):
    """三次贝塞尔曲线采样点"""
    t = np.linspace(0, 1, n)[:, None]
    P = np.array([a, b, c, d])
    return ((1-t)**3) @ P[0:1] + 3*((1-t)**2)*t @ P[1:2] + \
        3*(1-t)*t**2 @ P[2:3] + t**3 @ P[3:4]


# ---------- 2. 画布：21:9 画幅，三栏共用同一坐标比例 ----------
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
BLUE, RED, GREEN = '#0055cc', '#cc2222', '#00883a'
GHOST = '#999999'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]

SC, CY = 200, 350                        # 坐标比例与纵向中心


def T_factory(cx):
    return lambda p: ((p[0] - 1) * SC + cx, (p[1] - 0.75) * SC + CY)


def draw_control_polygon(T, pts, color, z=2):
    P = [T(p) for p in pts]
    ax.plot(*zip(*P), color=color, linestyle=(0, (3, 2.5)), linewidth=1,
            zorder=z)
    for i, q in enumerate(P):
        if i == 0 or i == len(P) - 1:
            ax.plot(*q, 'o', ms=4.5, color=color, zorder=z + 2)
        else:
            ax.plot(*q, 'o', ms=4.5, mfc='white', mec=color, mew=1.2,
                    zorder=z + 2)


def draw_curve(T, pts, color, lw=2.2, ls='-', z=3):
    xy = np.array([T(p) for p in cubic_pts(*pts)])
    ax.plot(xy[:, 0], xy[:, 1], color=color, linewidth=lw, linestyle=ls,
            zorder=z)


# ---------- 3. ① 原始曲线与分割点 ----------
CX1 = 300
T1 = T_factory(CX1)
ax.text(CX1, 608, "① 原始曲线（t = 0.3 处分割）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_control_polygon(T1, [p0, p1, p2, p3], GRAY)
draw_curve(T1, [p0, p1, p2, p3], BLUE)
for p, name, (dx, dy, ha, va) in [
        (p0, "p0 (0, 0)", (-10, -12, 'right', 'top')),
        (p1, "p1 (0.5, 1.5)", (-12, 10, 'right', 'bottom')),
        (p2, "p2 (1.5, 1.5)", (12, 10, 'left', 'bottom')),
        (p3, "p3 (2, 0)", (10, -12, 'left', 'top'))]:
    q = T1(p)
    ax.text(q[0] + dx, q[1] + dy, name, ha=ha, va=va, fontsize=10,
            path_effects=WHITE_STROKE, zorder=6)
q = T1(S_PT)
ax.plot(*q, 'o', ms=7, color=RED, zorder=5)
ax.text(q[0] - 14, q[1] + 10, "S（t = 0.3）", ha='right', va='bottom',
        fontsize=10.5, color=RED, path_effects=WHITE_STROKE, zorder=6)

# ①→② 箭头
ax.annotate('', xy=(670, 380), xytext=(560, 380),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(615, 414, "de Casteljau 构造", ha='center', va='center',
        fontsize=10.5, color='#333333', path_effects=WHITE_STROKE)

# ---------- 4. ② de Casteljau 逐级插值 ----------
CX2 = 972
T2 = T_factory(CX2)
ax.text(CX2, 608, "② de Casteljau 逐级插值（t = 0.3）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_curve(T2, [p0, p1, p2, p3], '#bcd2ea', lw=1.5, z=2)
draw_control_polygon(T2, [p0, p1, p2, p3], GRAY)
# 第一级：L0-L1、L1-L2（蓝）
ax.plot(*zip(T2(L0), T2(L1)), color=BLUE, linewidth=1.8, zorder=4)
ax.plot(*zip(T2(L1), T2(L2)), color=BLUE, linewidth=1.8, zorder=4)
# 第二级：M0-M1（绿）
ax.plot(*zip(T2(M0), T2(M1)), color=GREEN, linewidth=1.8, zorder=4)
for p, name, col, (dx, dy, ha, va) in [
        (L0, "L0", BLUE, (-12, 0, 'right', 'center')),
        (L1, "L1", BLUE, (0, 12, 'center', 'bottom')),
        (L2, "L2", BLUE, (12, 0, 'left', 'center')),
        (M0, "M0", GREEN, (-10, -6, 'right', 'top')),
        (M1, "M1", GREEN, (6, 10, 'left', 'bottom')),
        (S_PT, "S", RED, (0, -14, 'center', 'top'))]:
    q = T2(p)
    ax.plot(*q, 'o', ms=5.5 if name != 'S' else 7, color=col, zorder=5)
    ax.text(q[0] + dx, q[1] + dy, name, ha=ha, va=va, fontsize=10.5,
            color=col, fontweight='bold', path_effects=WHITE_STROKE,
            zorder=6)
# 子曲线控制点构成
ax.text(CX2, 178, "curve1 = (p0, L0, M0, S)", ha='center', va='center',
        fontsize=10.5, family='monospace', color=RED,
        path_effects=WHITE_STROKE)
ax.text(CX2, 142, "curve2 = (S, M1, L2, p3)", ha='center', va='center',
        fontsize=10.5, family='monospace', color=GREEN,
        path_effects=WHITE_STROKE)

# ②→③ 箭头
ax.annotate('', xy=(1360, 380), xytext=(1250, 380),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(1305, 414, "splitCubicAtT(..., 0.3)", ha='center', va='center',
        fontsize=10.5, color='#333333', path_effects=WHITE_STROKE)

# ---------- 5. ③ 分割结果：两条子贝塞尔曲线 ----------
CX3 = 1650
T3 = T_factory(CX3)
ax.text(CX3, 608, "③ 分割结果：两条子贝塞尔曲线", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
draw_curve(T3, [p0, p1, p2, p3], GHOST, lw=1.2, ls=(0, (4, 2.5)), z=2)
draw_control_polygon(T3, list(curve1), RED)
draw_control_polygon(T3, list(curve2), GREEN)
draw_curve(T3, list(curve1), RED, lw=2.4)
draw_curve(T3, list(curve2), GREEN, lw=2.4)
q = T3(S_PT)
ax.plot(*q, 'o', ms=7, color=RED, zorder=6)
ax.text(q[0] + 4, q[1] + 14, "S", ha='left', va='bottom', fontsize=10.5,
        color=RED, fontweight='bold', path_effects=WHITE_STROKE, zorder=6)
# 弧长核验（calcCubicArcLength 实测）
ax.text(CX3, 168, f"段 1 弧长 {len1:.4f} + 段 2 弧长 {len2:.4f} "
        f"= {len1 + len2:.4f} = 原曲线弧长", ha='center', va='center',
        fontsize=10.5, path_effects=WHITE_STROKE)

# ---------- 6. 底部图例带 ----------
ly1, ly2 = -85, -140
ax.plot([6, 34], [ly1, ly1], color=BLUE, linewidth=2.2)
ax.text(48, ly1, '原始曲线', va='center', fontsize=11)
ax.plot([220, 248], [ly1, ly1], color=GRAY, linestyle=(0, (3, 2.5)),
        linewidth=1)
ax.text(262, ly1, '控制多边形', va='center', fontsize=11)
ax.plot(440, ly1, 'o', ms=4.5, mfc='white', mec=GRAY, mew=1.2)
ax.text(454, ly1, '控制点', va='center', fontsize=11)
ax.plot([620, 648], [ly1, ly1], color=RED, linewidth=2.4)
ax.text(662, ly1, '子曲线 1 = (p0, L0, M0, S)', va='center', fontsize=11)
ax.plot([1000, 1028], [ly1, ly1], color=GREEN, linewidth=2.4)
ax.text(1042, ly1, '子曲线 2 = (S, M1, L2, p3)', va='center', fontsize=11)
ax.plot(1410, ly1, 'o', ms=6, color=RED)
ax.text(1424, ly1, '分割点 S（t = 0.3）', va='center', fontsize=11)
ax.text(20, ly2, 'de Casteljau：在控制多边形各边上按比例 t 逐级插值，'
        '最后一级插值点即曲线上的分割点，各级插值点即子曲线的控制点',
        va='center', fontsize=11, color='#444444')

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('splitcubic示意图.png', dpi=200)
fig.savefig('splitcubic示意图.pdf')
print('已生成 splitcubic示意图.png 与 splitcubic示意图.pdf（21:9）')
