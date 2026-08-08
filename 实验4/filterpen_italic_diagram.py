# -*- coding: utf-8 -*-
"""
实验4（附图）：filterPen 构建斜体过滤器示意图的生成
对应书稿「filterPen构建过滤器」一节：filterPen 通过创建自定义过滤器，
在字形绘制过程中自动改变路径的几何形状（缩放、平移、倾斜等），
字形的原始数据保持不变。本程序以思源宋体字符 “2” 为例，构建
ItalicFilterPen(FilterPen)：把每个点 (x, y) 改写为 (x + 0.25·y, y)，
即正体轮廓在绘制过程中被实时“剪切”为斜体（倾斜角 θ = arctan 0.25 ≈ 14°），
位移随高度线性增大——基线不动，越高右移越多。
示意图分三栏可视化这一转化过程：
  ① 正体 “2”：RecordingPen 直接记录的原始轮廓；
  ② ItalicFilterPen：过滤规则（代码 + 剪切示意网格）；
  ③ 斜体 “2”：过滤后的轮廓（灰虚线为叠加的原始轮廓），
     各高度处的位移箭头标明 位移 = 0.25·y。
要点：过滤器只改写坐标，指令序列的结构不变（两栏指令统计一致）。
输出：filterpen斜体示意图.png（位图）与 filterpen斜体示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.filterPen import FilterPen
from fontTools.pens.recordingPen import RecordingPen
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

SLANT = 0.25                               # 剪切系数：x' = x + SLANT·y
font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 思源宋体（CFF 三次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = '2'                                 # 测试字符：笔画含直线与曲线
glyphName = cmap[ord(char)]
g = glyphSet[glyphName]


class ItalicFilterPen(FilterPen):
    """自定义过滤器：正体 → 斜体。
    把每个点 (x, y) 改写为 (x + slant·y, y)（水平剪切），
    指令的类型与数量不变，仅坐标被改写。"""
    def __init__(self, outPen, slant):
        super().__init__(outPen)
        self.slant = slant

    def _pt(self, pt):
        x, y = pt
        return (x + self.slant * y, y)

    def moveTo(self, pt):
        self._outPen.moveTo(self._pt(pt))

    def lineTo(self, pt):
        self._outPen.lineTo(self._pt(pt))

    def curveTo(self, *pts):
        self._outPen.curveTo(*(self._pt(p) for p in pts))

    def qCurveTo(self, *pts):
        self._outPen.qCurveTo(*(self._pt(p) if p is not None else None
                                for p in pts))


# ---------- 1. 例程：原始记录 vs 经 ItalicFilterPen 过滤的记录 ----------
rec0 = RecordingPen()
g.draw(rec0)                               # 原始轮廓（正体）
rec1 = RecordingPen()
pen = ItalicFilterPen(rec1, slant=SLANT)
g.draw(pen)                                # 绘制过程中实时剪切为斜体
counts = Counter(c for c, _ in rec0.value)
assert Counter(c for c, _ in rec1.value) == counts   # 指令结构不变
print(f"字符 '{char}' → 字形 {glyphName}；指令统计 {dict(counts)}（两栏一致）")
print("首条指令对照：")
print(f"  过滤前 {rec0.value[0]}")
print(f"  过滤后 {rec1.value[0]}")


def recording_to_ops(value):
    """Pen 记录 → 线性指令流（本字体仅含三次曲线）"""
    ops, cur, start = [], None, None
    for cmd, pts in value:
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
            if pts[-1] is None:
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


ops0 = recording_to_ops(rec0.value)        # 正体
ops1 = recording_to_ops(rec1.value)        # 斜体
on0 = [op[-1] for op in ops0 if op[0] != 'closePath']   # 线上点（正体）
on1 = [op[-1] for op in ops1 if op[0] != 'closePath']   # 线上点（斜体）
allPts = [p for _, pts in rec0.value for p in pts]
xMin = min(p[0] for p in allPts)
xMax = max(p[0] for p in allPts)
yMax = max(p[1] for p in allPts)

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
GUIDES = (200, 400, 600)                   # 高度参考线


def fmt_pt(p):
    return "(" + ", ".join(str(int(v)) if float(v).is_integer()
                           else f"{v:.1f}" for v in p) + ")"


# ---------- 3. ① 正体（过滤前） ----------
ax.text(270, yMax + 40, "① 正体 '2'（过滤前）", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
ax.add_patch(PathPatch(ops_to_path(ops0), facecolor=FILL, edgecolor=BLACK,
                       linewidth=1.2, zorder=2))
ax.plot([p[0] for p in on0], [p[1] for p in on0], 'o', ms=2.8, color=BLACK,
        zorder=4)
for gy in GUIDES:                          # 高度参考线
    ax.plot([X0 + 20, 580], [gy, gy], color=GRAY, linestyle=':',
            linewidth=0.7, alpha=0.6, zorder=1)
    ax.text(X0 + 24, gy + 6, f'y = {gy}', ha='left', va='bottom',
            fontsize=8.5, color=GRAY)
ax.plot([0, 0], [Y0 + 200, yMax + 20], color=BLACK, linewidth=0.7, zorder=1)
ax.text(-6, yMax + 24, 'x = 0', ha='right', va='bottom', rotation=90,
        fontsize=9, color=BLACK)

# ---------- 4. ② 过滤规则：坐标改写公式 + 剪切示意网格 ----------
ax.text(965, yMax + 40, "② 过滤器：x' = x + 0.25·y",
        ha='center', va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
ax.text(965, 640, "每个点 (x, y) → (x + 0.25·y, y)", ha='center',
        va='center', fontsize=13, color=RED, path_effects=WHITE_STROKE)

# 剪切示意网格：竖线随高度倾斜（0..1000 映射到 400 单位）
gx, gy0, gs = 780, 90, 0.40                # 网格原点与比例
for i in range(5):                         # 正体网格（灰）
    xx = gx + i * 250 * gs
    ax.plot([xx, xx], [gy0, gy0 + 1000 * gs], color=GRAY, linewidth=0.7,
            alpha=0.7, zorder=2)
    yy = gy0 + i * 250 * gs
    ax.plot([gx, gx + 1000 * gs], [yy, yy], color=GRAY, linewidth=0.7,
            alpha=0.7, zorder=2)
for i in range(5):                         # 斜体网格（蓝）
    xx = gx + i * 250 * gs
    ax.plot([xx, xx + SLANT * 1000 * gs], [gy0, gy0 + 1000 * gs],
            color=BLUE, linewidth=1.0, zorder=3)
ax.text(gx, gy0 - 24, "剪切示意：竖线随高度倾斜",
        ha='left', va='top', fontsize=10, color=BLUE)

# ---------- 5. ③ 斜体（过滤后，叠加正体对比） ----------
def T(p):
    return (p[0] + DX3, p[1])


ax.text(270 + DX3, yMax + 40, "③ 斜体 '2'（过滤后）",
        ha='center', va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
for gy in GUIDES:
    ax.plot([DX3 - 60, DX3 + 580 + SLANT * yMax], [gy, gy], color=GRAY,
            linestyle=':', linewidth=0.7, alpha=0.6, zorder=1)
# 正体轮廓（灰虚线，叠加对比）
ax.add_patch(PathPatch(ops_to_path([(op[0],) + tuple(T(p) for p in op[1:])
                                    if op[0] != 'closePath' else op
                                    for op in ops0]),
                       fill=False, edgecolor=GRAY, linestyle='--',
                       linewidth=1.0, zorder=2))
# 斜体轮廓（过滤结果）
ax.add_patch(PathPatch(ops_to_path([(op[0],) + tuple(T(p) for p in op[1:])
                                    if op[0] != 'closePath' else op
                                    for op in ops1]),
                       facecolor=FILL, edgecolor=BLACK, linewidth=1.2,
                       zorder=3))
ax.plot([T(p)[0] for p in on0], [T(p)[1] for p in on0], 'o', ms=2.4,
        color=GRAY, zorder=4)
ax.plot([T(p)[0] for p in on1], [T(p)[1] for p in on1], 'o', ms=2.8,
        color=BLACK, zorder=5)

# 各高度位移箭头：位移 = SLANT·y
xa = xMax + DX3 + 40
for gy in (200, 400, 600, yMax):
    ax.annotate('', xy=(xa + SLANT * gy, gy), xytext=(xa, gy),
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.1))
    ax.text(xa + SLANT * gy / 2, gy + 12, f"+{SLANT * gy:.0f}",
            ha='center', va='bottom', fontsize=9.5, color=RED,
            path_effects=WHITE_STROKE)
ax.text(xa + SLANT * yMax + 10, yMax, "位移 = 0.25·y", ha='left',
        va='center', fontsize=10.5, color=RED, path_effects=WHITE_STROKE)

# 倾斜角指示：竖直（点线）vs 倾斜（红线）
tx = DX3 - 100
ax.plot([tx, tx], [0, 300], color=GRAY, linestyle=':', linewidth=1.0,
        zorder=2)
ax.plot([tx, tx + SLANT * 300], [0, 300], color=RED, linestyle='--',
        linewidth=1.2, zorder=2)
ax.text(tx + SLANT * 300 + 14, 150, "θ ≈ 14°", ha='left', va='center',
        fontsize=10.5, color=RED, path_effects=WHITE_STROKE)

# 基线 y=0（贯穿 ①③ 两栏）
ax.plot([X0 + 20, 580], [0, 0], color=BLACK, linestyle=(0, (12, 4)),
        linewidth=0.9, zorder=1)
ax.plot([DX3 - 100, xa + SLANT * yMax + 150], [0, 0], color=BLACK,
        linestyle=(0, (12, 4)), linewidth=0.9, zorder=1)
ax.text(X0 + 26, 8, '基线 y = 0', ha='left', va='bottom', fontsize=9.5,
        color=BLACK, path_effects=WHITE_STROKE)

# ---------- 6. 底部信息栏与图例 ----------
p0 = rec0.value[0][1][0]
p1 = rec1.value[0][1][0]
cnt = "、".join(f"{k} ×{v}" for k, v in counts.items())
info = [
    f"字符 '{char}'（U+{ord(char):04X}）→ {glyphName}（思源宋体）",
    f"指令结构不变：{cnt}（过滤前后一致）",
]
for i, line in enumerate(info):
    ax.text(DX3, -50 - i * 52, line, ha='left', va='center', fontsize=11)

ly = -80
lx = [20, 400, 800, 1130]
ax.plot([lx[0] - 14, lx[0] + 14], [ly, ly], color=GRAY, linestyle='--',
        linewidth=1.0)
ax.text(lx[0] + 24, ly, '正体轮廓（叠加对比）', va='center', fontsize=11,
        color=GRAY)
ax.add_patch(Rectangle((lx[1] - 12, ly - 9), 24, 18, facecolor=FILL,
                       edgecolor=BLACK, linewidth=1.0))
ax.text(lx[1] + 24, ly, '斜体轮廓（过滤后）', va='center', fontsize=11)
ax.annotate('', xy=(lx[2] + 14, ly), xytext=(lx[2] - 14, ly),
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.1))
ax.text(lx[2] + 24, ly, '位移箭头（= 0.25·y）', va='center', fontsize=11,
        color=RED)
ax.plot([lx[3] - 14, lx[3] + 14], [ly, ly], color=BLACK,
        linestyle=(0, (12, 4)), linewidth=0.9)
ax.text(lx[3] + 24, ly, '基线 y = 0', va='center', fontsize=11)

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('filterpen斜体示意图.png', dpi=200)
fig.savefig('filterpen斜体示意图.pdf')
print('已生成 filterpen斜体示意图.png 与 filterpen斜体示意图.pdf（21:9）')
