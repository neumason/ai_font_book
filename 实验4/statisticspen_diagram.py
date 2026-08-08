# -*- coding: utf-8 -*-
"""
实验4（附图）：StatisticsPen 字形面积矩统计信息示意图的生成
对应书稿「StatisticsPen字形的统计信息」一节的例程（lst:statisticspen1）：
    stats_pen = StatisticsPen(glyphSet)
    glyph.draw(stats_pen)
    print(stats_pen.meanX, stats_pen.stddevX, ..., stats_pen.slant)
StatisticsPen 继承 MomentsPen，在 glyph.draw(pen) 过程中用格林公式沿轮廓
累积面积矩，绘制结束后归一化为一组统计量（area、mean、variance/stddev、
covariance、correlation、slant），刻画轮廓【所围填充区域】的质量分布。
以思源黑体的 “一”“/”“虎” 三字为例，分三栏对比展示各统计量的几何含义：
  ① “一”：横向笔画，stddevX 远大于 stddevY，无倾斜；
  ② “/”：斜笔，correlation 接近 +1，slant 为正值；
  ③ “虎”：结构复杂，两个方向展开相近，correlation 接近 0。
每栏内容：灰色填充为统计对象（轮廓所围区域）；红十字线为质心
(meanX, meanY)；蓝虚线椭圆为协方差矩阵确定的 ±1σ 分布椭圆（半轴长即
两个方向的标准差）；绿实线为过质心、斜率为 slant 的拟合直线
x = meanX + slant·(y − meanY)；下方数值框为各统计量的实测结果。
所有统计量均由 StatisticsPen 真实计算。注意 slant = covariance/varianceY，
是 X 对 Y 的回归斜率（区别于 StatisticsControlPen 的控制多边形点集统计）。
输出：statisticspen示意图.png（位图）与 statisticspen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.statisticsPen import StatisticsPen
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyBboxPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("思源黑體ExtraLight.ttf")    # 思源黑体（TrueType 二次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
CHARS = ['一', '/', '虎']                  # 三个对比字符：横笔 / 斜笔 / 复杂结构
TITLES = ["① “一”：stddevX 远大于 stddevY，无倾斜",
          "② “/”：correlation 接近 +1，slant 为正",
          "③ “虎”：结构复杂，相关性接近 0"]

# ---------- 1. 真实执行书稿例程：逐字计算统计量 ----------
glyphs = []
for ch in CHARS:
    g = glyphSet[cmap[ord(ch)]]
    rec = RecordingPen()
    g.draw(rec)                            # 轮廓指令（供绘制路径用）
    stats_pen = StatisticsPen(glyphSet)
    g.draw(stats_pen)                      # 沿轮廓累积面积矩
    glyphs.append((ch, g, rec.value, stats_pen))
    print(f"{ch}: area={stats_pen.area:.0f} "
          f"mean=({stats_pen.meanX:.1f}, {stats_pen.meanY:.1f}) "
          f"stddev=({stats_pen.stddevX:.1f}, {stats_pen.stddevY:.1f}) "
          f"corr={stats_pen.correlation:.4f} slant={stats_pen.slant:.4f}")


def value_to_path(value, T):
    """RecordingPen 记录 → matplotlib Path（qCurveTo 补隐含线上点）。
    T 为坐标变换函数。"""
    verts, codes = [], []
    cur = start = None
    for cmd, pts in value:
        if cmd == 'moveTo':
            cur = start = pts[0]
            verts.append(T(cur)); codes.append(Path.MOVETO)
        elif cmd == 'lineTo':
            cur = pts[0]
            verts.append(T(cur)); codes.append(Path.LINETO)
        elif cmd == 'qCurveTo':
            pts = list(pts)
            oncurve = [pts[-1]]              # 末点为线上点
            for a, b in zip(pts[:-2], pts[1:-1]):  # 连续控制点间补隐含中点
                oncurve.insert(-1, ((a[0]+b[0])/2, (a[1]+b[1])/2))
            for c, e in zip(pts[:-1], oncurve):
                verts += [T(c), T(e)]
                codes += [Path.CURVE3, Path.CURVE3]
                cur = e
        elif cmd == 'closePath':
            verts.append(T(start)); codes.append(Path.CLOSEPOLY)
            cur = start
    return Path(verts, codes)


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
BLUE, RED, GREEN = '#0055cc', '#cc2222', '#007700'
FILL = '#dcebfb'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]

CX = [330, 1000, 1670]                   # 三栏中心
CY = 390                                 # 字形区中心高度
BOX_W, BOX_H = 430, 370                  # 单栏字形适配框

# ---------- 3. 逐栏绘制 ----------
for (ch, g, value, sp), cx, title in zip(glyphs, CX, TITLES):
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(glyphSet)
    g.draw(bp)
    xMin, yMin, xMax, yMax = bp.bounds
    s = min(BOX_W / (xMax - xMin), BOX_H / (yMax - yMin))
    dx = cx - (xMin + xMax) / 2 * s
    dy = CY - (yMin + yMax) / 2 * s

    def T(p, s=s, dx=dx, dy=dy):
        return (p[0] * s + dx, p[1] * s + dy)

    ax.text(cx, 608, title, ha='center', va='bottom', fontsize=13.5,
            fontweight='bold', path_effects=WHITE_STROKE)

    # 字形填充区域（统计对象）
    path = value_to_path(value, T)
    ax.add_patch(PathPatch(path, fc=FILL, ec='none', zorder=2))

    mean = T((sp.meanX, sp.meanY))
    # ±1σ 协方差椭圆：协方差矩阵特征分解，半轴长 = √特征值
    cov = np.array([[sp.varianceX, sp.covariance],
                    [sp.covariance, sp.varianceY]])
    lam, R = np.linalg.eigh(cov)
    t = np.linspace(0, 2 * np.pi, 120)
    m = np.array([[mean[0]], [mean[1]]])
    ell = m + (R * np.sqrt(np.abs(lam)) * s) @ \
        np.vstack([np.cos(t), np.sin(t)])
    ax.plot(ell[0], ell[1], color=BLUE, linestyle=(0, (5, 3)),
            linewidth=1.6, zorder=3)
    # 字形轮廓线
    ax.add_patch(PathPatch(path, fc='none', ec=BLACK, lw=1.5, zorder=4))
    # 质心十字线（红虚线）与质心标记
    x0, x1 = T((xMin, 0))[0] - 20, T((xMax, 0))[0] + 20
    y0, y1 = T((0, yMin))[1] - 20, T((0, yMax))[1] + 20
    ax.plot([mean[0], mean[0]], [y0, y1], color=RED, linestyle=(0, (4, 3)),
            linewidth=1.1, zorder=5)
    ax.plot([x0, x1], [mean[1], mean[1]], color=RED, linestyle=(0, (4, 3)),
            linewidth=1.1, zorder=5)
    # 拟合直线 x = meanX + slant·(y − meanY)（绿实线，限制在字形范围内）
    ys = np.array([T((0, yMin))[1], T((0, yMax))[1]])
    xs = mean[0] + sp.slant * (ys - mean[1])
    ax.plot(xs, ys, color=GREEN, linewidth=1.8, zorder=6)
    ax.plot(*mean, 'o', ms=7, mfc=RED, mec='white', mew=1.2, zorder=7)

    # 数值框：例程 print 的实测结果
    box = FancyBboxPatch((cx - 190, 8), 380, 172, boxstyle="round,pad=8",
                         fc='#f8f8f8', ec='#cccccc', lw=1, zorder=2)
    ax.add_patch(box)
    lines = [f"area   = {sp.area:.0f}",
             f"mean   = ({sp.meanX:.1f}, {sp.meanY:.1f})",
             f"stddev = ({sp.stddevX:.1f}, {sp.stddevY:.1f})",
             f"corr   = {sp.correlation:+.4f}",
             f"slant  = {sp.slant:+.4f}"]
    for i, line in enumerate(lines):
        ax.text(cx - 168, 148 - i * 32, line, ha='left', va='center',
                fontsize=10, family='monospace', zorder=3)

# ---------- 4. 底部图例带 ----------
ly1, ly2 = -85, -140
ax.add_patch(plt.Rectangle((6, ly1 - 10), 28, 20, fc=FILL, ec=BLACK,
                           lw=1.2))
ax.text(48, ly1, '字形填充区域（统计对象，按面积矩计算）', va='center',
        fontsize=11)
ax.plot([640, 668], [ly1, ly1], color=BLUE, linestyle=(0, (5, 3)),
        linewidth=1.6)
ax.text(682, ly1, '±1σ 协方差椭圆', va='center', fontsize=11)
ax.plot([1160, 1188], [ly1, ly1], color=RED, linestyle=(0, (4, 3)),
        linewidth=1.1)
ax.plot(1174, ly1, 'o', ms=6, mfc=RED, mec='white', mew=1.1)
ax.text(1202, ly1, '质心 (meanX, meanY)', va='center', fontsize=11)
ax.plot([1520, 1548], [ly1, ly1], color=GREEN, linewidth=1.8)
ax.text(1562, ly1, '拟合直线（斜率 slant）', va='center', fontsize=11)
ax.text(20, ly2, '数值框为各统计量的实测结果；area 带符号，TrueType '
        '顺时针外轮廓为负值', va='center', fontsize=11, color='#444444')

# ---------- 5. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('statisticspen示意图.png', dpi=200)
fig.savefig('statisticspen示意图.pdf')
print('已生成 statisticspen示意图.png 与 statisticspen示意图.pdf（21:9）')
