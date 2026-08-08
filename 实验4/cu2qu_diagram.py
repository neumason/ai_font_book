# -*- coding: utf-8 -*-
"""
实验4（附图）：Cu2QuPen 的 TrueType 转换示意图的生成
对应书稿「Cu2QuPen的TrueType转换」一节的例程（lst:example116）：
    recordingPen = RecordingPen()
    cu2qupen = Cu2QuPen(recordingPen, max_err=1.0)  # 3次贝塞尔 → 2次贝塞尔
    g.draw(cu2qupen)
    convertedpath = recordingPen.value
以思源宋体（CFF 轮廓，三次贝塞尔）的字符 “S” 为例，分三栏可视化转换过程：
  ① 转换前：原始轮廓由 12 段三次贝塞尔曲线构成（○ 为三次曲线控制点）；
  ② 转换后：同一字形变为 27 段二次贝塞尔曲线（□ 为离曲线控制点，
     相邻控制点之间隐含的线上点也一并标出）；
  ③ 局部放大：一段三次曲线如何被 3 段二次曲线在 max_err = 1.0 之内逼近，
     偏差连线按比例放大绘出。
Cu2QuPen 逐段独立转换（curveTo → qCurveTo），与书中整字形绘制的
结果完全一致；stats 参数统计各三次曲线分裂出的二次段数。
输出：cu2qu转换示意图.png（位图）与 cu2qu转换示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.cu2qu import curve_to_quadratic
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

MAX_ERR = 1.0                              # 书稿例程指定的最大误差（字体单位）
font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 思源宋体（CFF 三次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = 'S'                                 # 测试字符：全曲线、单轮廓，便于展示
glyphName = cmap[ord(char)]
g = glyphSet[glyphName]
upm = font['head'].unitsPerEm

# ---------- 1. 书稿例程：Cu2QuPen 把三次轮廓绘制为二次轮廓 ----------
recCubic = RecordingPen()
g.draw(recCubic)                           # 原始轮廓（三次贝塞尔）
stats = {}                                 # 统计：每段三次曲线分裂为几段二次
recordingPen = RecordingPen()
cu2qupen = Cu2QuPen(recordingPen, max_err=MAX_ERR, stats=stats)
g.draw(cu2qupen)                           # 绘制过程中完成 3 次 → 2 次转换
convertedpath = recordingPen.value         # 转换后的轮廓（二次贝塞尔）
print(f"字符 '{char}' → 字形 {glyphName}；Cu2QuPen stats = {stats}")


def recording_to_ops(value):
    """把 Pen 记录的轮廓指令展开为线性指令流，qCurveTo 按 TrueType 语义
    拆成单段二次曲线（连续控制点之间补上隐含的线上点中点）。
    返回 (ops, implied)：ops 为 ('moveTo',p) / ('lineTo',p) /
    ('curveTo',c1,c2,p) / ('quadTo',c,p) / ('closePath',) 的列表，
    implied 为隐含线上点（控制点中点）的坐标列表。"""
    ops, implied, cur, start = [], [], None, None
    for cmd, pts in value:
        pts = list(pts)
        if cmd == "moveTo":
            cur = start = pts[0]
            ops.append(('moveTo', cur))
        elif cmd == "lineTo":
            cur = pts[0]
            ops.append(('lineTo', cur))
        elif cmd == "curveTo":             # 三次贝塞尔（CFF 轮廓）
            ops.append(('curveTo', pts[0], pts[1], pts[2]))
            cur = pts[2]
        elif cmd == "qCurveTo":            # 二次贝塞尔（TrueType 轮廓）
            if pts[-1] is None:            # 结尾 None 表示绕回轮廓起点
                pts[-1] = start
            offs = pts[:-1]
            ons = [cur]
            for a, b in zip(offs, offs[1:]):
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                ons.append(mid)
                implied.append(mid)        # 隐含的线上点
            ons.append(pts[-1])
            for i, off in enumerate(offs):
                ops.append(('quadTo', off, ons[i + 1]))
            cur = pts[-1]
        elif cmd in ("closePath", "endPath"):
            ops.append(('closePath',))
    return ops, implied


opsC, _ = recording_to_ops(recCubic.value)   # 原始：三次
opsQ, impliedQ = recording_to_ops(convertedpath)  # 转换后：二次
nCubic = sum(1 for op in opsC if op[0] == 'curveTo')
nQuad = sum(1 for op in opsQ if op[0] == 'quadTo')
print(f"三次曲线段 {nCubic} → 二次曲线段 {nQuad}")


def ops_to_path(ops):
    """指令流 → matplotlib Path（字体坐标，基线为 y=0）"""
    verts, codes = [], []
    for op in ops:
        if op[0] == 'moveTo':
            codes.append(Path.MOVETO); verts.append(op[1])
        elif op[0] == 'lineTo':
            codes.append(Path.LINETO); verts.append(op[1])
        elif op[0] == 'curveTo':
            codes += [Path.CURVE4] * 3; verts += [op[1], op[2], op[3]]
        elif op[0] == 'quadTo':
            codes += [Path.CURVE3] * 2; verts += [op[1], op[2]]
        elif op[0] == 'closePath':
            codes.append(Path.CLOSEPOLY); verts.append((0, 0))
    return Path(verts, codes)


def cubic_pt(p, t):
    mt = 1 - t
    return (mt**3 * p[0][0] + 3 * mt * mt * t * p[1][0] +
            3 * mt * t * t * p[2][0] + t**3 * p[3][0],
            mt**3 * p[0][1] + 3 * mt * mt * t * p[1][1] +
            3 * mt * t * t * p[2][1] + t**3 * p[3][1])


def quad_pt(q, t):
    mt = 1 - t
    return (mt * mt * q[0][0] + 2 * mt * t * q[1][0] + t * t * q[2][0],
            mt * mt * q[0][1] + 2 * mt * t * q[1][1] + t * t * q[2][1])


def quads_of(cubic):
    """用与 Cu2QuPen 相同的 curve_to_quadratic 单独转换一段三次曲线，
    返回 [(起点, 控制点, 终点), ...] 二次段列表（含隐含线上点）"""
    r = curve_to_quadratic(cubic, MAX_ERR, True)
    offs = r[1:-1]
    ons = [r[0]] + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                    for a, b in zip(offs, offs[1:])] + [r[-1]]
    return [(ons[i], offs[i], ons[i + 1]) for i in range(len(offs))]


def deviation(cubic, quads, n=240):
    """实测三次曲线与二次逼近之间的最大偏差（采样法）；
    二次曲线按每段 1000 点加密采样，避免采样间距把偏差值虚增；
    返回 (最大偏差, 三次曲线上的最偏点, 二次曲线上最近点)"""
    C = np.array([cubic_pt(cubic, t / (n - 1)) for t in range(n)])
    Q = np.concatenate([[quad_pt(q, t / 999) for t in range(1000)]
                        for q in quads])
    d2 = ((C[:, None, :] - Q[None, :, :]) ** 2).sum(-1)
    i = d2.min(1).argmax()               # 三次曲线上偏差最大的采样点
    j = d2[i].argmin()                   # 二次曲线上距其最近的采样点
    return float(np.sqrt(d2[i, j])), tuple(C[i]), tuple(Q[j])


# ---------- 2. 逐段分析：每段三次曲线 → 几段二次曲线、实测偏差 ----------
cur = None
segments = []                              # [(cubic, quads, dev), ...]
for op in opsC:
    if op[0] in ('moveTo', 'lineTo'):
        cur = op[1]
    elif op[0] == 'curveTo':
        cubic = (cur, op[1], op[2], op[3])
        quads = quads_of(cubic)
        dev, _, _ = deviation(cubic, quads)
        segments.append((cubic, quads, dev))
        print(f"  段{len(segments) - 1}: 1 次 → {len(quads)} 段二次，"
              f"实测最大偏差 {dev:.4f}")
        cur = op[3]
maxDev = max(s[2] for s in segments)
print(f"全字形实测最大偏差 ≈ {maxDev:.2f} ≤ max_err = {MAX_ERR}")

# 放大对象：分裂段数最多、偏差最大的那段三次曲线
zi = max(range(len(segments)),
         key=lambda i: (len(segments[i][1]), segments[i][2]))
zCubic, zQuads, zDev = segments[zi]
print(f"放大段 = 段{zi}（1 → {len(zQuads)} 段二次，偏差 {zDev:.2f}）")

# ---------- 3. 收集绘图要素：线上点、控制点、控制多边形 ----------
onC = [op[-1] for op in opsC if op[0] != 'closePath']       # 三次线上点
onQ = [op[-1] for op in opsQ if op[0] != 'closePath']       # 二次线上点(含隐含)
offQ = [op[1] for op in opsQ if op[0] == 'quadTo']          # 二次离曲线控制点
polyC = []                       # 三次控制柄：(线上点, 控制点) 线段
cur = None
for op in opsC:
    if op[0] in ('moveTo', 'lineTo'):
        cur = op[1]
    elif op[0] == 'curveTo':
        polyC += [(cur, op[1]), (op[2], op[3])]
        cur = op[3]
polyQ = []                       # 二次控制多边形：线上点—控制点交替
cur = None
for op in opsQ:
    if op[0] in ('moveTo', 'lineTo'):
        cur = op[1]
    elif op[0] == 'quadTo':
        polyQ += [(cur, op[1]), (op[1], op[2])]
        cur = op[2]

xs = [p[0] for p in onC + [c for seg in polyC for c in seg]]
ys = [p[1] for p in onC + [c for seg in polyC for c in seg]]
xMin, xMax, yMin, yMax = min(xs), max(xs), min(ys), max(ys)

# ---------- 4. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
DX = (xMax - xMin) + 560                   # ②栏平移量（含标题与栏距）
Y0, Y1 = -300, 900                         # 视图纵范围（底部留图例带）
XR = (Y1 - Y0) * 21 / 9                    # 按 21:9 推出横向范围
X0, X1 = -140, -140 + XR
fig = plt.figure(figsize=(12.6, 5.4))      # 12.6 : 5.4 = 21 : 9
ax = fig.add_axes([0, 0, 1, 1])            # 坐标区充满整幅，保证输出严格 21:9
ax.set_xlim(X0, X1)
ax.set_ylim(Y0, Y1)
ax.set_aspect('equal')
ax.axis('off')

BLACK, GRAY = 'black', '#777777'
BLUE, RED, GREEN = '#0055cc', '#cc2222', '#007755'
FILL = '#e8e8e8'
ZX0, ZX1 = xMax + DX + 160, X1 - 60        # ③栏（局部放大）横范围
ZY0, ZY1 = 120, 780                        # ③栏纵范围（下方留信息栏）


def sh(p):
    """②栏坐标：整体右移 DX"""
    return (p[0] + DX, p[1])


def draw_glyph(ops, shift, poly, offpts, implied, title, title_x):
    """画一栏字形：填充轮廓 + 控制多边形 + 线上点 + 控制点标记"""
    tr = (lambda p: sh(p)) if shift else (lambda p: p)
    path = ops_to_path([(op[0],) + tuple(tr(p) for p in op[1:])
                        if op[0] != 'closePath' else op for op in ops])
    ax.add_patch(PathPatch(path, facecolor=FILL, edgecolor=BLACK,
                           linewidth=1.0, zorder=2))
    for a, b in poly:                        # 控制柄 / 控制多边形
        ax.plot([tr(a)[0], tr(b)[0]], [tr(a)[1], tr(b)[1]],
                color=BLUE if not shift else RED, linewidth=0.6,
                alpha=0.65, zorder=3)
    onpts = [op[-1] for op in ops if op[0] != 'closePath']
    ax.plot([tr(p)[0] for p in onpts], [tr(p)[1] for p in onpts], 'o',
            ms=3.2, color=BLACK, zorder=4)
    if offpts:                               # 控制点标记
        mk = dict(marker='o', mfc='white', mec=BLUE) if not shift else \
             dict(marker='s', mfc='white', mec=RED)
        ax.plot([tr(p)[0] for p in offpts], [tr(p)[1] for p in offpts],
                linestyle='none', ms=4.2, mew=1.1, zorder=4, **mk)
    if implied:                              # 隐含线上点（控制点中点）
        ax.plot([tr(p)[0] for p in implied], [tr(p)[1] for p in implied],
                'o', ms=2.4, color=RED, zorder=5)
    ax.text(title_x, yMax + 46, title, ha='center', va='bottom',
            fontsize=13.5, fontweight='bold',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])


ctrlC = [op[i] for op in opsC if op[0] == 'curveTo' for i in (1, 2)]
draw_glyph(opsC, False, polyC, ctrlC, None,
           f"① 转换前：三次贝塞尔（CFF / OTF）· {nCubic} 段", (xMin + xMax) / 2)
draw_glyph(opsQ, True, polyQ, offQ, impliedQ,
           f"② Cu2QuPen 转换后：二次贝塞尔（TrueType）· {nQuad} 段",
           (xMin + xMax) / 2 + DX)

# 基线 y=0（贯穿 ①② 两栏）
ax.plot([X0 + 60, xMax + DX + 60], [0, 0], color=BLACK,
        linestyle=(0, (12, 4)), linewidth=0.9, zorder=1)
ax.text(X0 + 66, 10, '基线 y = 0', ha='left', va='bottom',
        fontsize=10, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])

# ---------- 5. ③ 局部放大：一段三次 → 多段二次 ----------
# 放大区在原图上的位置（①② 两栏各画一个虚线框标示）
zs = list(zCubic) + [q[1] for q in zQuads]
bx0 = min(p[0] for p in zs) - 10
bx1 = max(p[0] for p in zs) + 10
by0 = min(p[1] for p in zs) - 10
by1 = max(p[1] for p in zs) + 10
for dx in (0, DX):
    ax.add_patch(Rectangle((bx0 + dx, by0), bx1 - bx0, by1 - by0,
                           fill=False, edgecolor=GREEN, linestyle='--',
                           linewidth=1.1, zorder=5))
    ax.text(bx0 + 5 + dx, by1 - 5, '③', ha='left', va='top', fontsize=11,
            color=GREEN, fontweight='bold',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])

# 偏差连线放大倍数：使最偏连线长度适中
MAGN = next(m for m in (100, 50, 20, 10)
            if zDev * m <= 0.09 * (ZY1 - ZY0))

# 放大变换：以曲线包围盒为中心，控制点与放大后的偏差连线全部纳入，
# 等比缩放到 ③ 栏矩形
pad = zDev * MAGN + 30
curvePts = [cubic_pt(zCubic, t / 100) for t in range(101)]
cxs = [p[0] for p in curvePts]
cys = [p[1] for p in curvePts]
zx, zy = (min(cxs) + max(cxs)) / 2, (min(cys) + max(cys)) / 2
zw = 2 * max(max(p[0] for p in zs) - zx, zx - min(p[0] for p in zs)) + 2 * pad
zh = 2 * max(max(p[1] for p in zs) - zy, zy - min(p[1] for p in zs)) + 2 * pad
s = min((ZX1 - ZX0) / zw, (ZY1 - ZY0) / zh)
cx, cy = (ZX0 + ZX1) / 2, (ZY0 + ZY1) / 2


def Z(p):
    return ((p[0] - zx) * s + cx, (p[1] - zy) * s + cy)


ax.add_patch(Rectangle((ZX0, ZY0), ZX1 - ZX0, ZY1 - ZY0,
                       facecolor='#fafafa', edgecolor=GRAY,
                       linewidth=0.8, zorder=1))
ax.text(cx, ZY1 + 14, f"③ 局部放大：1 段三次 → {len(zQuads)} 段二次",
        ha='center', va='bottom', fontsize=13.5, fontweight='bold')

# 三次曲线（蓝实线）与二次逼近（红虚线）几乎重合
ts = np.linspace(0, 1, 200)
ax.plot(*zip(*[Z(cubic_pt(zCubic, t)) for t in ts]), color=BLUE,
        linewidth=2.4, zorder=3)
for q in zQuads:
    ax.plot(*zip(*[Z(quad_pt(q, t)) for t in ts]), color=RED,
            linestyle=(0, (5, 3)), linewidth=1.3, zorder=4)

# 偏差连线（×MAGN 放大）：三次采样点 → 二次曲线上最近点
Q = np.concatenate([[quad_pt(q, t / 999) for t in range(1000)]
                    for q in zQuads])
for t in np.linspace(0.06, 0.94, 7):
    c = np.array(cubic_pt(zCubic, t))
    qpt = Q[((Q - c) ** 2).sum(1).argmin()]
    tip = c + (qpt - c) * MAGN
    ax.plot([Z(c)[0], Z(tip)[0]], [Z(c)[1], Z(tip)[1]],
            color=GREEN, linewidth=0.9, zorder=5)
dev, cMax, qMax = deviation(zCubic, zQuads)
tipMax = np.array(cMax) + (np.array(qMax) - np.array(cMax)) * MAGN
ax.annotate(f"实测最大偏差 ≈ {dev:.2f} ≤ max_err = {MAX_ERR}\n"
            f"（偏差连线 ×{MAGN} 放大）",
            xy=Z(tipMax), xytext=(ZX0 + 20, ZY0 + 88),
            fontsize=11.5, color=GREEN,
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.0),
            ha='left', va='center', zorder=6)

# 控制点：三次 ○（蓝）、二次 □（红）；线上点 ●；隐含线上点（小红点）
for a, b in ((zCubic[0], zCubic[1]), (zCubic[2], zCubic[3])):
    ax.plot([Z(a)[0], Z(b)[0]], [Z(a)[1], Z(b)[1]], color=BLUE,
            linestyle=':', linewidth=0.9, zorder=4)
ax.plot(*zip(*[Z(p) for p in zCubic[1:3]]), 'o', ms=5.5, mfc='white',
        mec=BLUE, mew=1.2, linestyle='none', zorder=5)
qp = []
cur = zCubic[0]
for q in zQuads:
    qp += [(cur, q[1]), (q[1], q[2])]
    cur = q[2]
for a, b in qp:
    ax.plot([Z(a)[0], Z(b)[0]], [Z(a)[1], Z(b)[1]], color=RED,
            linestyle=':', linewidth=0.9, zorder=4)
ax.plot(*zip(*[Z(q[1]) for q in zQuads]), 's', ms=5.5, mfc='white',
        mec=RED, mew=1.2, linestyle='none', zorder=5)
ax.plot(*zip(*[Z(q[2]) for q in zQuads[:-1]]), 'o', ms=3.0, color=RED,
        linestyle='none', zorder=5)
ax.plot(*zip(*[Z(zCubic[0]), Z(zCubic[3])]), 'o', ms=5.0, color=BLACK,
        linestyle='none', zorder=6)

# ---------- 6. 右栏信息栏 ----------
def fmt(p):
    return "(" + ", ".join(str(int(v)) if float(v).is_integer()
                           else f"{v:.1f}" for v in p) + ")"


firstC = next(op for op in opsC if op[0] == 'curveTo')
firstQ = next(v for c, v in convertedpath if c == 'qCurveTo')
midQ = ((firstQ[0][0] + firstQ[1][0]) / 2, (firstQ[0][1] + firstQ[1][1]) / 2)
info = [
    f"字符 '{char}'（U+{ord(char):04X}）→ {glyphName}",
    f"思源宋体（CFF 三次轮廓，upm = {upm}）",
    "Cu2QuPen(recordingPen, max_err = 1.0)",
    f"三次 {nCubic} 段 → 二次 {nQuad} 段"
    f"（1→2 ×{stats.get('2', 0)}，1→3 ×{stats.get('3', 0)}）",
    f"全字形实测最大偏差 ≈ {maxDev:.2f} ≤ max_err",
    "curveTo(" + ", ".join(fmt(p) for p in firstC[1:]) + ")",
    "→ qCurveTo(" + ", ".join(fmt(p) for p in firstQ) + ")",
    f"  两控制点间隐含线上点 {fmt(midQ)}",
]
for i, line in enumerate(info):
    ax.text(ZX0, 64 - i * 46, line, ha='left', va='center', fontsize=11)

# ---------- 7. 底部图例带 ----------
ly1, ly2 = -150, -215
lx = [X0 + 80, X0 + 700, X0 + 1290]
ax.plot(lx[0], ly1, 'o', ms=4, color=BLACK)
ax.text(lx[0] + 26, ly1, '线上点（on-curve）', va='center', fontsize=12)
ax.plot(lx[1], ly1, 'o', ms=5, mfc='white', mec=BLUE, mew=1.2)
ax.text(lx[1] + 26, ly1, '三次曲线控制点', va='center', fontsize=12, color=BLUE)
ax.plot(lx[2], ly1, 's', ms=5, mfc='white', mec=RED, mew=1.2)
ax.text(lx[2] + 26, ly1, '二次离曲线控制点', va='center',
        fontsize=12, color=RED)
ax.plot(lx[0], ly2, 'o', ms=3, color=RED)
ax.text(lx[0] + 26, ly2, '隐含线上点（相邻控制点中点）', va='center',
        fontsize=12, color=RED)
ax.plot([lx[1] - 12, lx[1] + 12], [ly2, ly2], color=GRAY, linestyle=':',
        linewidth=1.2)
ax.text(lx[1] + 26, ly2, '控制柄 / 控制多边形', va='center', fontsize=12)
ax.add_patch(Rectangle((lx[2] - 12, ly2 - 9), 24, 18, fill=False,
                       edgecolor=GREEN, linestyle='--', linewidth=1.1))
ax.text(lx[2] + 26, ly2, '放大区位置 → ③', va='center',
        fontsize=12, color=GREEN)

# ---------- 8. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('cu2qu转换示意图.png', dpi=200)
fig.savefig('cu2qu转换示意图.pdf')
print('已生成 cu2qu转换示意图.png 与 cu2qu转换示意图.pdf（21:9）')
