# -*- coding: utf-8 -*-
"""
实验4（附图）：PointPen 构建自定义字形变换示意图的生成
对应书稿「PointPen构建自定义字形变换」一节的例程（lst:example2121321216）：
    class NarrowPointPen(AbstractPointPen):  # 把所有点的 x 坐标压缩为 k 倍
        def addPoint(self, pt, segmentType=None, ...):
            self.outPen.addPoint((x * self.k, y), segmentType, ...)
    glyph.drawPoints(NarrowPointPen(rec1, k=0.6))
以思源黑体（TrueType 轮廓）字符 “O” 为例，分三栏可视化 PointPen 的用途：
  ① PointPen 的点级视图：drawPoints 把轮廓作为一串有序的点发给笔——
     线上点（segmentType 为 'qcurve'）与离曲线控制点（segmentType 为
     None）全部可见，共 2 条轮廓 32 个点（附记录摘录）；
  ② 点级变换规则：每个点 (x, y) → (0.6·x, y)（水平压缩网格示意）；
  ③ 窄体 “O”：每个点（含控制点）逐一改写后的结果，
     灰虚线为叠加的原始轮廓，红色箭头为对应点的位移。
程序真实执行例程并断言：rec1 的每个点恰为 rec0 对应点的 x×0.6。
输出：pointpen示意图.png（位图）与 pointpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.pointPen import AbstractPointPen, PointToSegmentPen
from fontTools.pens.recordingPen import RecordingPen, RecordingPointPen
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

K = 0.6                                    # 窄体压缩系数
font = TTFont("思源黑體ExtraLight.ttf")    # 思源黑体（TrueType 二次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = 'O'                                 # 测试字符：内外两条全曲线轮廓
glyphName = cmap[ord(char)]
glyph = glyphSet[glyphName]


class NarrowPointPen(AbstractPointPen):
    """自定义 PointPen：把所有点的 x 坐标压缩为 k 倍（窄体）"""
    def __init__(self, outPen, k):
        self.outPen = outPen
        self.k = k

    def beginPath(self, identifier=None):
        self.outPen.beginPath(identifier)

    def addPoint(self, pt, segmentType=None, smooth=False, name=None,
                 identifier=None):
        x, y = pt
        self.outPen.addPoint((x * self.k, y), segmentType, smooth, name,
                             identifier)

    def endPath(self):
        self.outPen.endPath()

    def addComponent(self, baseGlyph, transformation):
        self.outPen.addComponent(baseGlyph, transformation)


# ---------- 1. 真实执行例程：变换前后的点级记录 ----------
rec0 = RecordingPointPen()
glyph.drawPoints(rec0)                     # 点级记录（原始）
rec1 = RecordingPointPen()
glyph.drawPoints(NarrowPointPen(rec1, k=K))  # 绘制过程中逐点压缩
pts0 = [a[0] for c, a, _ in rec0.value if c == 'addPoint']
pts1 = [a[0] for c, a, _ in rec1.value if c == 'addPoint']
seg0 = [a[1] for c, a, _ in rec0.value if c == 'addPoint']
onPts = [p for p, s in zip(pts0, seg0) if s is not None]   # 线上点
offPts = [p for p, s in zip(pts0, seg0) if s is None]      # 离曲线控制点
for (x0, y0), (x1, y1) in zip(pts0, pts1):
    assert abs(x1 - x0 * K) < 1e-9 and y1 == y0    # 逐点验证 x×0.6
nPath = sum(1 for c, _, _ in rec0.value if c == 'beginPath')
print(f"字符 '{char}'（U+{ord(char):04X}）→ 字形 {glyphName}")
print(f"{nPath} 条轮廓共 {len(pts0)} 点：线上点 {len(onPts)}、"
      f"控制点 {len(offPts)}；rec1 各点 = rec0 各点 x×{K}（断言通过）")
print("变换前:", [tuple(a[0]) for c, a, _ in rec0.value if c == 'addPoint'][:3])
print("变换后:", [tuple(a[0]) for c, a, _ in rec1.value if c == 'addPoint'][:3])


def point_rec_to_ops(value):
    """RecordingPointPen 记录 → 段命令 → 线性指令流
    （经 PointToSegmentPen 转换，qCurveTo 按 TrueType 语义展开隐含点）"""
    rec = RecordingPen()
    pen = PointToSegmentPen(rec)
    for cmd, args, kwargs in value:
        getattr(pen, cmd)(*args, **kwargs)
    ops, cur, start = [], None, None
    for cmd, pts in rec.value:
        pts = list(pts)
        if cmd == "moveTo":
            cur = start = pts[0]
            ops.append(('moveTo', cur))
        elif cmd == "lineTo":
            cur = pts[0]
            ops.append(('lineTo', cur))
        elif cmd == "curveTo":
            ops.append(('curveTo', pts[0], pts[1], pts[2]))
            cur = pts[2]
        elif cmd == "qCurveTo":
            if pts[-1] is None:            # 结尾 None 表示绕回轮廓起点
                pts[-1] = start
            offs = pts[:-1]
            ons = [cur] + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                           for a, b in zip(offs, offs[1:])] + [pts[-1]]
            for i, off in enumerate(offs):
                ops.append(('quadTo', off, ons[i + 1]))
            cur = pts[-1]
        elif cmd in ("closePath", "endPath"):
            ops.append(('closePath',))
    return ops


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


ops0 = point_rec_to_ops(rec0.value)        # 原始轮廓
ops1 = point_rec_to_ops(rec1.value)        # 窄体轮廓
xMin = min(p[0] for p in pts0)
xMax = max(p[0] for p in pts0)
yMax = max(p[1] for p in pts0)
# 内轮廓（第 2 条）包围盒，用于放置记录摘录
paths = [p for c, a, _ in rec0.value if c == 'addPoint' for p in [a[0]]]
second = rec0.value.index(next(v for i, v in enumerate(rec0.value)
                               if i > 0 and v[0] == 'beginPath'))
inPts = [a[0] for c, a, _ in rec0.value[second:] if c == 'addPoint']
icx = (min(p[0] for p in inPts) + max(p[0] for p in inPts)) / 2
icy = (min(p[1] for p in inPts) + max(p[1] for p in inPts)) / 2

# ---------- 2. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
Y0, Y1 = -170, 830                         # 视图纵范围（底部留图例带）
XR = (Y1 - Y0) * 21 / 9                    # 按 21:9 推出横向范围
X0, X1 = -10, -10 + XR
fig = plt.figure(figsize=(12.6, 5.4))      # 12.6 : 5.4 = 21 : 9
ax = fig.add_axes([0, 0, 1, 1])            # 坐标区充满整幅，保证输出严格 21:9
ax.set_xlim(X0, X1)
ax.set_ylim(Y0, Y1)
ax.set_aspect('equal')
ax.axis('off')

BLACK, GRAY = 'black', '#777777'
BLUE, RED = '#0055cc', '#cc2222'
FILL = '#e8e8e8'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]
DX3 = 1250                                 # ③栏平移量

# ---------- 3. ① PointPen 的点级视图 ----------
ax.text(357, yMax + 40, "① PointPen 的点级视图（32 个点）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
ax.add_patch(PathPatch(ops_to_path(ops0), facecolor=FILL, edgecolor=BLACK,
                       linewidth=1.1, zorder=2))
ax.plot([p[0] for p in onPts], [p[1] for p in onPts], 'o', ms=3.6,
        color=BLACK, zorder=4)
ax.plot([p[0] for p in offPts], [p[1] for p in offPts], 'o', ms=4.2,
        mfc='white', mec=BLUE, mew=1.1, linestyle='none', zorder=4)
ax.plot([X0 + 20, xMax + 80], [0, 0], color=BLACK, linestyle=(0, (12, 4)),
        linewidth=0.9, zorder=1)
ax.text(X0 + 26, 8, '基线 y = 0', ha='left', va='bottom', fontsize=9.5,
        color=BLACK, path_effects=WHITE_STROKE)
# 记录摘录（数据，非代码）：放在内轮廓空白处
excerpt = [(a[0], a[1]) for c, a, _ in rec0.value if c == 'addPoint'][:3]
ax.text(icx, icy + 70, "记录摘录", ha='center', va='center', fontsize=9.5,
        color=GRAY, zorder=5)
for i, (p, seg) in enumerate(excerpt):
    ax.text(icx, icy + 30 - i * 40,
            f"({p[0]}, {p[1]})  {seg}", ha='center', va='center',
            fontsize=9, family='monospace', zorder=5,
            path_effects=WHITE_STROKE)

# ---------- 4. ② 点级变换规则 ----------
ax.text(950, yMax + 40, "② 点级变换（窄体）", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
ax.text(950, 620, "(x, y) → (0.6·x, y)", ha='center', va='center',
        fontsize=13, color=RED, path_effects=WHITE_STROKE)
# 水平压缩网格：0..1000 映射到 300 单位（灰原网格 + 蓝压缩竖线）
gx, gy0, gs = 800, 180, 0.30
for i in range(5):
    xx = gx + i * 250 * gs
    ax.plot([xx, xx], [gy0, gy0 + 1000 * gs], color=GRAY, linewidth=0.7,
            alpha=0.7, zorder=2)
    yy = gy0 + i * 250 * gs
    ax.plot([gx, gx + 1000 * gs], [yy, yy], color=GRAY, linewidth=0.7,
            alpha=0.7, zorder=2)
for i in range(5):                         # 压缩后：x × 0.6
    xx = gx + i * 250 * gs * K
    ax.plot([xx, xx], [gy0, gy0 + 1000 * gs], color=BLUE, linewidth=1.0,
            zorder=3)
ax.text(gx, gy0 - 24, "水平压缩：x × 0.6", ha='left', va='top',
        fontsize=10, color=BLUE)

# ---------- 5. ③ 窄体 'O'（每个点 x×0.6） ----------
def T(p):
    return (p[0] + DX3, p[1])


ax.text(1600, yMax + 40, "③ 窄体 'O'（每个点 x×0.6）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
ax.add_patch(PathPatch(ops_to_path([(op[0],) + tuple(T(p) for p in op[1:])
                                    if op[0] != 'closePath' else op
                                    for op in ops0]),
                       fill=False, edgecolor=GRAY, linestyle='--',
                       linewidth=1.0, zorder=2))
ax.add_patch(PathPatch(ops_to_path([(op[0],) + tuple(T(p) for p in op[1:])
                                    if op[0] != 'closePath' else op
                                    for op in ops1]),
                       facecolor=FILL, edgecolor=BLACK, linewidth=1.1,
                       zorder=3))
ax.plot([T(p)[0] for p in onPts], [T(p)[1] for p in onPts], 'o', ms=2.6,
        color=GRAY, zorder=4)
# 对应点的位移箭头（取右侧 3 个点）
for p in [(652, 365), (569, 638), (357, 739)]:
    ax.annotate('', xy=T((p[0] * K, p[1])), xytext=T(p),
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.1))
ax.plot([DX3 - 60, xMax + DX3 + 80], [0, 0], color=BLACK,
        linestyle=(0, (12, 4)), linewidth=0.9, zorder=1)
info = [
    f"字符 '{char}'（U+{ord(char):04X}）→ 思源黑体 ExtraLight（TrueType）",
    f"{nPath} 条轮廓共 {len(pts0)} 点：{len(onPts)} 线上 + "
    f"{len(offPts)} 控制，逐一改写",
]
for i, line in enumerate(info):
    ax.text(DX3 + 110, -50 - i * 52, line, ha='left', va='center',
            fontsize=11)

# ---------- 6. 底部图例带 ----------
ly = -80
lx = [20, 340, 740, 1120]
ax.plot(lx[0], ly, 'o', ms=3.6, color=BLACK)
ax.text(lx[0] + 26, ly, "线上点（'qcurve'）", va='center', fontsize=11)
ax.plot(lx[1], ly, 'o', ms=4.2, mfc='white', mec=BLUE, mew=1.1)
ax.text(lx[1] + 26, ly, '离曲线控制点（None）', va='center',
        fontsize=11, color=BLUE)
ax.annotate('', xy=(lx[2] + 14, ly), xytext=(lx[2] - 14, ly),
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.1))
ax.text(lx[2] + 26, ly, '点的位移（x×0.6）', va='center', fontsize=11,
        color=RED)
ax.plot([lx[3] - 14, lx[3] + 14], [ly, ly], color=GRAY, linestyle='--',
        linewidth=1.0)
ax.text(lx[3] + 26, ly, '原轮廓（叠加对比）', va='center', fontsize=11,
        color=GRAY)

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('pointpen示意图.png', dpi=200)
fig.savefig('pointpen示意图.pdf')
print('已生成 pointpen示意图.png 与 pointpen示意图.pdf（21:9）')
