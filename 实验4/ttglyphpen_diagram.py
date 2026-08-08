# -*- coding: utf-8 -*-
"""
实验4（附图）：TTGlyphPen 修改字符曲线示意图的生成
对应书稿「ttGlyphPen修改字符曲线」一节的例程（lst:ttglyphpen1）：
    glyph.draw(recordingPen, glyfTable)      # 记录：捕获原始路径
    for command, coords in recordingPen.value:  # 修改：逐条改写坐标
        ...
    newGlyph = newGlyphPen.glyph()           # 重建：生成新 Glyph 对象
    glyfTable[glyphName] = newGlyph          # 写回 glyf 表
以思源黑体（TrueType 二次轮廓）的字符 “1” 为例，分三栏可视化
“记录→修改→重建”流程：
  ① 记录：RecordingPen 捕获的原始路径（绿方块为 moveTo 起点，
     红圈为 qCurveTo 离曲线控制点）；
  ② 修改：按命令类型改写坐标的规则与实测示例——moveTo/lineTo
     端点平移 (+100,+100)，qCurveTo 各点平移 (+100,+50)，
     closePath 原样转发；
  ③ 重建：TTGlyphPen 生成的新字形（浅蓝填充）与原始轮廓（灰虚线）
     叠加——直线部分与曲线部分的位移不同，顶部产生相对错位；
     指令类型与数量不变（12 条），新字形可写回 glyf 表保存。
本程序真实执行完整流水线（含重建后重新记录验证）。
输出：ttglyphpen示意图.png（位图）与 ttglyphpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyBboxPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['font.monospace'] = ['DejaVu Sans Mono', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("思源黑體ExtraLight.ttf")    # 思源黑体（TrueType 二次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = '1'                                 # 书稿例程所用字符
glyphName = cmap[ord(char)]
glyfTable = font['glyf']
glyph = glyfTable[glyphName]

# ---------- 1. 真实执行书稿例程：记录 → 修改 → 重建 ----------
recordingPen = RecordingPen()
glyph.draw(recordingPen, glyfTable)          # 记录：捕获原始路径
orig = recordingPen.value

newGlyphPen = TTGlyphPen(glyphSet)
for command, coords in orig:                 # 修改：按命令类型改写坐标
    if command == "moveTo":
        newGlyphPen.moveTo((coords[0][0] + 100, coords[0][1] + 100))
    elif command == "lineTo":
        newGlyphPen.lineTo((coords[0][0] + 100, coords[0][1] + 100))
    elif command == "qCurveTo":
        newGlyphPen.qCurveTo(*[(c[0] + 100, c[1] + 50) for c in coords])
    elif command == "closePath":
        newGlyphPen.closePath()

newGlyph = newGlyphPen.glyph()               # 重建：生成新 Glyph 对象
rec2 = RecordingPen()
newGlyph.draw(rec2, glyfTable)               # 重新记录验证
mod = rec2.value
print(f"指令数 原/新：{len(orig)}/{len(mod)}；命令序列一致：",
      [c for c, _ in orig] == [c for c, _ in mod])
print("原始  首条:", orig[0], " 曲线:", orig[5])
print("修改后首条:", mod[0], " 曲线:", mod[5])


def value_to_path(value, T):
    """RecordingPen 记录 → matplotlib Path（qCurveTo 补隐含线上点）"""
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


def decompose(value):
    """RecordingPen 记录 → 逐段几何（kind ∈ move/line/quad/close）"""
    segs = []
    cur = start = None
    for cmd, pts in value:
        if cmd == 'moveTo':
            cur = start = pts[0]
            segs.append(('move', (cur,)))
        elif cmd == 'lineTo':
            segs.append(('line', (cur, pts[0]))); cur = pts[0]
        elif cmd == 'qCurveTo':
            pts = list(pts)
            oncurve = [pts[-1]]
            for a, b in zip(pts[:-2], pts[1:-1]):
                oncurve.insert(-1, ((a[0]+b[0])/2, (a[1]+b[1])/2))
            for c, e in zip(pts[:-1], oncurve):
                segs.append(('quad', (cur, c, e))); cur = e
        elif cmd == 'closePath':
            segs.append(('close', (cur, start))); cur = start
    return segs


def quad_pts(p0, c, p1, npts=40):
    """二次贝塞尔曲线采样点"""
    t = np.linspace(0, 1, npts)[:, None]
    P = np.array([p0, c, p1])
    return ((1-t)**2) @ P[0:1] + 2*(1-t)*t @ P[1:2] + t**2 @ P[2:3]


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
FILL, GHOST = '#dcebfb', '#999999'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]

S = 0.55                                 # ①③ 两栏共用同一比例

# ---------- 3. ① 记录：RecordingPen 捕获原始路径 ----------
CX1, DY1 = 300, 120
DX1 = CX1 - (95 + 453) / 2 * S


def T1(p):
    return (p[0] * S + DX1, p[1] * S + DY1)


ax.text(CX1, 608, "① 记录：RecordingPen 捕获原始路径", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
for kind, pts in decompose(orig):
    P = [T1(p) for p in pts]
    if kind == 'move':
        ax.plot(*P[0], 's', ms=7, color=GREEN, zorder=5)
        ax.text(P[0][0] - 12, P[0][1] - 12, "(95, 33)", ha='right',
                va='top', fontsize=10, color=GREEN,
                path_effects=WHITE_STROKE, zorder=6)
    elif kind == 'line':
        ax.plot(*zip(*P), color=BLACK, linewidth=2.2, zorder=3)
        ax.plot(*P[1], 'o', ms=4.5, color=BLACK, zorder=4)
    elif kind == 'quad':
        xy = np.array([T1(p) for p in quad_pts(*pts)])
        ax.plot(xy[:, 0], xy[:, 1], color=RED, linewidth=2.2, zorder=3)
        ax.plot(*zip(P[0], P[1]), color=RED, linestyle=':',
                linewidth=0.9, zorder=3)
        ax.plot(*zip(P[1], P[2]), color=RED, linestyle=':',
                linewidth=0.9, zorder=3)
        ax.plot(*P[1], 'o', ms=5.5, mfc='white', mec=RED, mew=1.3,
                zorder=4)
        ax.text(P[1][0] - 10, P[1][1] + 12, "(216, 697)", ha='right',
                va='bottom', fontsize=10, color=RED,
                path_effects=WHITE_STROKE, zorder=6)
        ax.plot(*P[2], 'o', ms=4.5, color=BLACK, zorder=4)
    elif kind == 'close':
        ax.plot(*zip(*P), color=GRAY, linestyle=(0, (4, 2.5)),
                linewidth=1.2, zorder=2)
ax.text(T1((262, 658))[0] + 12, T1((262, 658))[1], "(262, 658)",
        ha='left', va='center', fontsize=10,
        path_effects=WHITE_STROKE, zorder=6)

# ①→② 箭头
ax.annotate('', xy=(635, 320), xytext=(545, 320),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(590, 352, "recordingPen.value", ha='center', va='center',
        fontsize=10.5, color='#333333', path_effects=WHITE_STROKE)

# ---------- 4. ② 修改：逐条改写坐标 ----------
CX2 = 972
ax.text(CX2, 608, "② 修改：逐条改写坐标", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
frame = FancyBboxPatch((650, 15), 645, 530, boxstyle="round,pad=10",
                       fc='#f8f8f8', ec='#cccccc', lw=1, zorder=0)
ax.add_patch(frame)
ax.text(672, 505, "改写规则：", ha='left', va='center', fontsize=10.5,
        color=GRAY, zorder=3)
ax.text(672, 465, "moveTo / lineTo:  (x, y) → (x+100, y+100)",
        ha='left', va='center', fontsize=10, family='monospace',
        color=BLACK, zorder=3)
ax.text(672, 429, "qCurveTo:         (x, y) → (x+100, y+50)",
        ha='left', va='center', fontsize=10, family='monospace',
        color=RED, zorder=3)
ax.text(672, 393, "closePath:", ha='left', va='center',
        fontsize=10, family='monospace', color=GRAY, zorder=3)
ax.text(812, 393, "原样转发", ha='left', va='center',
        fontsize=10, color=GRAY, zorder=3)
ax.text(672, 345, "实测示例：", ha='left', va='center', fontsize=10.5,
        color=GRAY, zorder=3)
for i, (tag, tok, col) in enumerate([
        ("原:", f"('moveTo', ((95, 33),))", BLACK),
        ("新:", f"('moveTo', ((195, 133),))", BLUE),
        ("原:", f"('qCurveTo', ((216, 697), (266, 726)))", BLACK),
        ("新:", f"('qCurveTo', ((316, 747), (366, 776)))", BLUE)]):
    ax.text(672, 305 - i * 32, tag, ha='left', va='center',
            fontsize=10, color=col, zorder=3)
    ax.text(722, 305 - i * 32, tok, ha='left', va='center',
            fontsize=9.5, family='monospace', color=col, zorder=3)
ax.text(672, 305 - 4 * 32 - 16, "指令类型与数量不变（12 条），仅坐标被改写",
        ha='left', va='center', fontsize=10.5, color=GRAY, zorder=3)

# ②→③ 箭头
ax.annotate('', xy=(1445, 320), xytext=(1325, 320),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(1385, 352, "newGlyphPen.glyph()", ha='center', va='center',
        fontsize=10.5, color='#333333', path_effects=WHITE_STROKE)

# ---------- 5. ③ 重建：TTGlyphPen 生成新字形 ----------
CX3, DY3 = 1650, 320 - (0 + 826) / 2 * S
DX3 = CX3 - (95 + 553) / 2 * S           # 原始与修改共用坐标系


def T3(p):
    return (p[0] * S + DX3, p[1] * S + DY3)


ax.text(CX3, 608, "③ 重建：TTGlyphPen 生成新字形", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
# 原始轮廓（灰虚线）
path_o = value_to_path(orig, T3)
ax.add_patch(PathPatch(path_o, fc='none', ec=GHOST, lw=1.3,
                       linestyle=(0, (4, 2.5)), zorder=2))
# 新字形（浅蓝填充）
path_m = value_to_path(mod, T3)
ax.add_patch(PathPatch(path_m, fc=FILL, ec='none', zorder=3))
ax.add_patch(PathPatch(path_m, fc='none', ec=BLACK, lw=1.8, zorder=4))
# 位移箭头：moveTo 起点 (95,33) → (195,133)
p_from, p_to = T3((95, 33)), T3((195, 133))
ax.annotate('', xy=p_to, xytext=p_from,
            arrowprops=dict(arrowstyle='-|>', lw=1.8, color=BLUE,
                            mutation_scale=15), zorder=6)
ax.plot(*p_from, 's', ms=6, mfc='white', mec=GREEN, mew=1.3, zorder=5)
ax.plot(*p_to, 's', ms=7, color=GREEN, zorder=5)
ax.text(p_from[0] - 12, p_from[1] - 30, "(+100, +100)", ha='right',
        va='center', fontsize=10, color=BLUE,
        path_effects=WHITE_STROKE, zorder=6)
ax.text(p_to[0] + 12, p_to[1], "(195, 133)", ha='left', va='center',
        fontsize=10, color=GREEN, path_effects=WHITE_STROKE, zorder=6)
# 顶部曲线段位移说明
ax.text(T3((330, 826))[0], T3((330, 826))[1] + 14,
        "曲线段 (+100, +50)", ha='center', va='bottom', fontsize=10,
        color=RED, path_effects=WHITE_STROKE, zorder=6)

# ---------- 6. 底部图例带 ----------
ly1, ly2 = -85, -140
ax.plot(20, ly1, 's', ms=7, color=GREEN)
ax.text(42, ly1, 'moveTo 起点（③ 含新位置）', va='center', fontsize=11)
ax.plot(400, ly1, 'o', ms=5.5, mfc='white', mec=RED, mew=1.3)
ax.text(422, ly1, 'qCurveTo 离曲线控制点', va='center', fontsize=11)
ax.plot([760, 788], [ly1, ly1], color=GHOST, linestyle=(0, (4, 2.5)),
        linewidth=1.3)
ax.text(802, ly1, '原始轮廓（③ 中叠加显示）', va='center', fontsize=11)
ax.add_patch(plt.Rectangle((1100, ly1 - 10), 28, 20, fc=FILL, ec=BLACK,
                           lw=1.2))
ax.text(1142, ly1, 'TTGlyphPen 重建的新字形', va='center', fontsize=11)
ax.text(20, ly2, '位移规则：直线点 (+100, +100)，曲线点 (+100, +50)；'
        '新字形写回 glyf 表后 font.save 保存', va='center', fontsize=11,
        color='#444444')

# ---------- 7. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('ttglyphpen示意图.png', dpi=200)
fig.savefig('ttglyphpen示意图.pdf')
print('已生成 ttglyphpen示意图.png 与 ttglyphpen示意图.pdf（21:9）')
