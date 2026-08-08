# -*- coding: utf-8 -*-
"""
实验4（附图）：RecordingPen 捕获字形绘制过程示意图的生成
对应书稿「RecordingPen捕获字形绘制过程」一节的例程（lst:recordingpen1）：
    recordingPen = RecordingPen()
    glyph.draw(recordingPen)      # 捕获：全部绘图命令被记录到 value
    ...
    recordingPen.replay(pen)      # 重放：把记录逐条发给另一支 Pen
以思源黑体（TrueType 二次轮廓）的字符 “1” 为例，分三栏可视化“记录—重放”过程：
  ① 捕获：glyph.draw(recordingPen) 依次发出的 12 条指令（1 次 moveTo、
     9 次 lineTo、1 次 qCurveTo、1 次 closePath），路径上的序号与指令
     一一对应，蓝色箭头标示绘制方向；
  ② 记录：recordingPen.value 保存的指令流（元素为 (命令, 坐标) 元组），
     一条 qCurveTo 记录携带 2 个连续控制点（红色行）；
  ③ 重放：recordingPen.replay(pen) 按记录逐条重画，得到与原始轮廓
     完全一致的路径（灰虚线为偏移显示的原始轮廓）。
本程序真实执行捕获与重放，并校验重放结果与原始记录逐条一致。
输出：recordingpen示意图.png（位图）与 recordingpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, FancyBboxPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("思源黑體ExtraLight.ttf")    # 思源黑体（TrueType 二次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = '1'                                 # 书稿例程所用字符
glyph = glyphSet[cmap[ord(char)]]

# ---------- 1. 真实执行书稿例程：捕获 → 重放 → 校验 ----------
recordingPen = RecordingPen()
glyph.draw(recordingPen)                   # 捕获：记录全部绘图命令
rec2 = RecordingPen()
recordingPen.replay(rec2)                  # 重放：逐条发给另一支 Pen
assert rec2.value == recordingPen.value
n = len(recordingPen.value)
from collections import Counter
print(f"字符 '{char}'：recordingPen.value 共 {n} 条指令，",
      dict(Counter(c for c, _ in recordingPen.value)))
print("重放结果与原始记录逐条一致：", rec2.value == recordingPen.value)

# ---------- 2. 把记录展开为逐段几何（qCurveTo 补隐含线上点） ----------
segs = []          # (idx, cmd, kind, pts)：kind ∈ move/line/quad/close
cur = start = None
for i, (cmd, pts) in enumerate(recordingPen.value):
    if cmd == 'moveTo':
        cur = start = pts[0]
        segs.append((i, cmd, 'move', (cur,)))
    elif cmd == 'lineTo':
        segs.append((i, cmd, 'line', (cur, pts[0])))
        cur = pts[0]
    elif cmd == 'qCurveTo':
        pts = list(pts)
        oncurve = [pts[-1]]                  # 末点为线上点
        for a, b in zip(pts[:-2], pts[1:-1]):  # 连续控制点之间补隐含中点
            oncurve.insert(-1, ((a[0]+b[0])/2, (a[1]+b[1])/2))
        ctrls = pts[:-1]
        for k, (c, e) in enumerate(zip(ctrls, oncurve)):
            segs.append((i, cmd, 'quad', (cur, c, e)))
            cur = e
    elif cmd == 'closePath':
        segs.append((i, cmd, 'close', (cur, start)))
        cur = start


def quad_pts(p0, c, p1, npts=40):
    """二次贝塞尔曲线采样点"""
    t = np.linspace(0, 1, npts)[:, None]
    P = np.array([p0, c, p1])
    return ((1-t)**2) @ P[0:1] + 2*(1-t)*t @ P[1:2] + t**2 @ P[2:3]


# ---------- 3. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
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
GHOST = '#888888'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]
CMD_COLOR = {'moveTo': GREEN, 'lineTo': BLACK,
             'qCurveTo': RED, 'closePath': GRAY}

# 字形缩放与两栏平移量（①③ 两栏共用同一比例）
from fontTools.pens.boundsPen import BoundsPen
bp = BoundsPen(glyphSet)
glyph.draw(bp)
xMin, yMin, xMax, yMax = bp.bounds
S = 0.55                                 # 726 字高 → 约 400 图单位
CX1, CX3 = 250, 1620                     # ①③ 两栏字形中心
DY = 70                                  # 基线高度
DX1 = CX1 - (xMin + xMax) / 2 * S
DX3 = CX3 - (xMin + xMax) / 2 * S


def T(p, dx):
    return (p[0] * S + dx, p[1] * S + DY)


# ---------- 4. ① 捕获：glyph.draw(recordingPen) ----------
ax.text(CX1, 590, "① 捕获：glyph.draw(recordingPen)", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)

for idx, cmd, kind, pts in segs:
    col = CMD_COLOR[cmd]
    P = [T(p, DX1) for p in pts]
    if kind == 'move':
        ax.plot(*P[0], 's', ms=7, color=GREEN, zorder=5)   # 起点：绿方块
    elif kind == 'line':
        ax.plot(*zip(*P), color=BLACK, linewidth=2.2, zorder=3)
        ax.plot(*P[1], 'o', ms=4.5, color=BLACK, zorder=4)
    elif kind == 'quad':
        xy = np.array([T(p, DX1) for p in quad_pts(*pts)])
        ax.plot(xy[:, 0], xy[:, 1], color=RED, linewidth=2.2, zorder=3)
        ax.plot(*zip(P[0], P[1]), color=RED, linestyle=':',
                linewidth=0.9, zorder=3)                   # 控制多边形
        ax.plot(*zip(P[1], P[2]), color=RED, linestyle=':',
                linewidth=0.9, zorder=3)
        ax.plot(*P[1], 'o', ms=5.5, mfc='white', mec=RED, mew=1.3,
                zorder=4)                                  # 离曲线控制点
        ax.plot(*P[2], 'o', ms=4.5, color=BLACK, zorder=4)
    elif kind == 'close':
        ax.plot(*zip(*P), color=GRAY, linestyle=(0, (4, 2.5)),
                linewidth=1.2, zorder=2)

# 指令序号标注（与 ② 栏 recordingPen.value 一一对应）
LBL_OFF = {0: (0, 13, 'center', 'bottom'), 1: (0, 12, 'center', 'bottom'),
           2: (-12, 0, 'right', 'center'), 3: (0, -14, 'center', 'top'),
           4: (-11, 0, 'right', 'center'), 5: (-16, 12, 'right', 'bottom'),
           6: (0, 11, 'center', 'bottom'), 7: (12, 0, 'left', 'center'),
           8: (0, 12, 'center', 'bottom'), 9: (11, 0, 'left', 'center'),
           10: (0, -13, 'center', 'top'), 11: (-11, 0, 'right', 'center')}
for idx, cmd, kind, pts in segs:
    P = [T(p, DX1) for p in pts]
    if kind == 'move':
        mid = P[0]
    elif kind == 'quad':
        mid = tuple((np.array(P[0]) + 2*np.array(P[1]) + np.array(P[2])) / 4)
    else:
        mid = tuple((np.array(P[0]) + np.array(P[1])) / 2)
    dx, dy, ha, va = LBL_OFF[idx]
    ax.text(mid[0] + dx, mid[1] + dy, str(idx), ha=ha, va=va, fontsize=10,
            fontweight='bold', color=CMD_COLOR[cmd],
            path_effects=WHITE_STROKE, zorder=6)

# 绘制方向箭头（蓝色）：沿 stem 两侧长边与底边
for xy, xytext in [((243.4, 290), (243.4, 240)),
                   ((262.7, 240), (262.7, 290)),
                   ((215, 70), (265, 70))]:
    ax.annotate('', xy=xy, xytext=xytext,
                arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                                mutation_scale=14), zorder=6)

# ①→② 箭头
ax.annotate('', xy=(632, 300), xytext=(420, 300),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(526, 332, "glyph.draw(recordingPen)", ha='center', va='center',
        fontsize=11, color='#333333', path_effects=WHITE_STROKE)

# ---------- 5. ② 记录：recordingPen.value ----------
CX2 = 972
ax.text(CX2, 590, f"② 记录：recordingPen.value（{n} 条指令）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
frame = FancyBboxPatch((650, 15), 645, 530, boxstyle="round,pad=10",
                       fc='#f8f8f8', ec='#cccccc', lw=1, zorder=0)
ax.add_patch(frame)
Y_START, Y_STEP = 505, 42
for i, entry in enumerate(recordingPen.value):
    y = Y_START - i * Y_STEP
    if entry[0] == 'qCurveTo':               # 高亮 qCurveTo 记录
        ax.add_patch(Rectangle((658, y - Y_STEP / 2), 629, Y_STEP,
                               fc='#fdeaea', ec='none', zorder=1))
    ax.text(672, y, f"{i:2d}  {entry!r}", ha='left', va='center',
            fontsize=9.5, family='monospace', color=CMD_COLOR[entry[0]],
            zorder=3)
ax.text(CX2, -32, "红色行：一条 qCurveTo 记录携带 2 个连续控制点",
        ha='center', va='center', fontsize=10.5, color=RED)

# ②→③ 箭头
ax.annotate('', xy=(1495, 300), xytext=(1315, 300),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(1405, 332, "recordingPen.replay(pen)", ha='center', va='center',
        fontsize=11, color='#333333', path_effects=WHITE_STROKE)

# ---------- 6. ③ 重放：recordingPen.replay(pen) ----------
ax.text(CX3, 590, "③ 重放：recordingPen.replay(pen)", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)

# 由记录重建 matplotlib Path（replay 的结果）
verts, codes = [], []
for idx, cmd, kind, pts in segs:
    P = [T(p, DX3) for p in pts]
    if kind == 'move':
        verts.append(P[0]); codes.append(Path.MOVETO)
    elif kind == 'line':
        verts.append(P[1]); codes.append(Path.LINETO)
    elif kind == 'quad':
        verts += [P[1], P[2]]
        codes += [Path.CURVE3, Path.CURVE3]
    elif kind == 'close':
        verts.append(P[0]); codes.append(Path.CLOSEPOLY)
path = Path(verts, codes)

# 灰虚线：偏移显示的原始轮廓（与重放路径完全重合）
ghost = Path([(x + 12, y + 12) for x, y in verts], codes)
ax.add_patch(PathPatch(ghost, fc='none', ec=GHOST, lw=1.3, linestyle='--',
                       zorder=2))
ax.add_patch(PathPatch(path, fc='#dcebfb', ec=BLACK, lw=2, zorder=3))
for idx, cmd, kind, pts in segs:
    P = [T(p, DX3) for p in pts]
    if kind == 'move':
        ax.plot(*P[0], 's', ms=7, color=GREEN, zorder=5)
    elif kind == 'line':
        ax.plot(*P[1], 'o', ms=4.5, color=BLACK, zorder=5)
    elif kind == 'quad':
        ax.plot(*zip(P[0], P[1]), color=RED, linestyle=':',
                linewidth=0.9, zorder=4)
        ax.plot(*zip(P[1], P[2]), color=RED, linestyle=':',
                linewidth=0.9, zorder=4)
        ax.plot(*P[1], 'o', ms=5.5, mfc='white', mec=RED, mew=1.3, zorder=5)
        ax.plot(*P[2], 'o', ms=4.5, color=BLACK, zorder=5)
ax.text(CX3, 40, f"{n} 条指令逐一重放，路径与原始轮廓完全一致",
        ha='center', va='top', fontsize=11, path_effects=WHITE_STROKE)

# ---------- 7. 底部图例带 ----------
ly1, ly2 = -85, -140
ax.plot(20, ly1, 's', ms=7, color=GREEN)
ax.text(42, ly1, 'moveTo 起点', va='center', fontsize=11)
ax.plot([366, 394], [ly1, ly1], color=BLACK, linewidth=2.2)
ax.text(402, ly1, 'lineTo 直线段', va='center', fontsize=11)
ax.plot([706, 734], [ly1, ly1], color=RED, linewidth=2.2)
ax.text(742, ly1, 'qCurveTo 二次曲线段', va='center', fontsize=11)
ax.plot(1150, ly1, 'o', ms=5.5, mfc='white', mec=RED, mew=1.3)
ax.text(1172, ly1, '离曲线控制点（qCurveTo 的中间点）', va='center',
        fontsize=11)
ax.plot([6, 34], [ly2, ly2], color=GRAY, linestyle='--', linewidth=1.2)
ax.text(42, ly2, 'closePath 闭合边', va='center', fontsize=11)
ax.annotate('', xy=(334, ly2), xytext=(306, ly2),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14))
ax.text(342, ly2, '绘制方向', va='center', fontsize=11)
ax.add_patch(Rectangle((626, ly2 - 10), 28, 20, fc='none', ec=GHOST,
                       linestyle='--', lw=1.3))
ax.text(662, ly2, '③ 中灰虚线为偏移显示的原始轮廓', va='center',
        fontsize=11)
ax.text(1100, ly2, '路径序号与 recordingPen.value 中的指令一一对应',
        va='center', fontsize=11)

# ---------- 8. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('recordingpen示意图.png', dpi=200)
fig.savefig('recordingpen示意图.pdf')
print('已生成 recordingpen示意图.png 与 recordingpen示意图.pdf（21:9）')
