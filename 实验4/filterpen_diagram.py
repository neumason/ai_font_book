# -*- coding: utf-8 -*-
"""
实验4（附图）：filterPen 构建过滤器示意图的生成
对应书稿「filterPen构建过滤器」一节的例程（lst:example216）：
    class MyFilterPen(FilterPen):
        def __init__(self, outPen):
            super().__init__(outPen)
        def lineTo(self, pt):
            self._outPen.moveTo(pt)        # 将 lineTo 转换为 moveTo
例程向 MyFilterPen 依次发送 moveTo / lineTo / curveTo / closePath，
lineTo 在绘制过程中被改写为 moveTo（抬笔），其余指令原样转发给
RecordingPen。本程序真实执行该例程，并分三栏可视化改写过程：
  ① 指令流：左为输入指令，右为 RecordingPen 实际记录的结果，
     被改写的 lineTo → moveTo 以红色标出；
  ② 若不过滤：指令原样执行的路径——lineTo 段把起点 (100, 100)
     与 (200, 200) 连成线，closePath 闭合回起点；
  ③ 过滤后：lineTo 段不再绘制（灰虚线为消失段），轮廓起点变为
     (200, 200)，closePath 也随之闭合到 (200, 200)；
     (100, 100) 处留下一个没有绘制内容的空轮廓。
注意：例程各点坐标均在对角线 y = x 上，路径退化为对角线往返，
图中 closePath 闭合边稍加偏移以便分辨（图例已注明）。
输出：filterpen示意图.png（位图）与 filterpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.pens.filterPen import FilterPen
from fontTools.pens.recordingPen import RecordingPen
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


class MyFilterPen(FilterPen):
    """书稿例程：把所有 lineTo 命令改写为 moveTo"""
    def __init__(self, outPen):
        super().__init__(outPen)

    def lineTo(self, pt):
        # 将 lineTo 转换为 moveTo
        self._outPen.moveTo(pt)


# ---------- 1. 真实执行书稿例程 ----------
recordingPen = RecordingPen()
pen = MyFilterPen(recordingPen)
cmds = [                                   # 例程发送的指令序列
    ("moveTo", [(100, 100)]),
    ("lineTo", [(200, 200)]),
    ("curveTo", [(300, 300), (400, 400), (500, 500)]),
    ("closePath", []),
]
for cmd, args in cmds:
    getattr(pen, cmd)(*args)
print("RecordingPen 实际记录：")
for command, points in recordingPen.value:
    print(f"{command}: {points}")
# 与输入指令逐条比对，找出被改写的行
changed = [i for i, (c, _) in enumerate(cmds)
           if recordingPen.value[i][0] != c]
print(f"被改写的指令：第 {changed} 条（lineTo → moveTo）")


def fmt_pt(p):
    return f"({p[0]}, {p[1]})"


def call_lines(cmd, args):
    """输入指令 → 'pen.xxx(...)' 文本（过长时折行）"""
    body = ", ".join(fmt_pt(a) for a in args)
    if len(f"pen.{cmd}({body})") <= 30:
        return [f"pen.{cmd}({body})"]
    return [f"pen.{cmd}({fmt_pt(args[0])}),",
            "        " + ", ".join(fmt_pt(a) for a in args[1:]) + ")"]


def rec_lines(cmd, pts):
    """记录结果 → 'cmd: (...)' 文本（与例程 print 输出一致，过长折行）"""
    if not pts:
        return [f"{cmd}: ()"]
    body = "(" + ", ".join(fmt_pt(p) for p in pts) + \
        ("," if len(pts) == 1 else "") + ")"
    if len(f"{cmd}: {body}") <= 30:
        return [f"{cmd}: {body}"]
    return [f"{cmd}: ({fmt_pt(pts[0])}),",
            "          " + ", ".join(fmt_pt(p) for p in pts[1:]) + ")"]


# ---------- 2. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
Y0, Y1 = -170, 680                         # 视图纵范围（底部留图例带）
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
GHOST = '#999999'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]
SQRT2 = 2 ** 0.5

# ---------- 3. ① 指令流的改写（左栏） ----------
ax.text(350, 590, "① MyFilterPen：lineTo → moveTo",
        ha='center', va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
ax.text(20, 545, "输入指令", ha='left', va='center', fontsize=11.5,
        color=GRAY)
ax.text(400, 545, "recordingPen.value", ha='left', va='center',
        fontsize=11.5, color=GRAY)
y = 498
for i, ((cmd, args), (rcmd, rpts)) in enumerate(zip(cmds,
                                                    recordingPen.value)):
    col = RED if i in changed else BLACK
    for j, line in enumerate(call_lines(cmd, args)):
        ax.text(20, y - j * 46, line, ha='left', va='center', fontsize=10,
                color=col, family='monospace',
                path_effects=WHITE_STROKE)
    for j, line in enumerate(rec_lines(rcmd, rpts)):
        ax.text(400, y - j * 46, line, ha='left', va='center', fontsize=10,
                color=col, family='monospace',
                path_effects=WHITE_STROKE)
    nlines = max(len(call_lines(cmd, args)), len(rec_lines(rcmd, rpts)))
    ax.annotate('', xy=(390, y), xytext=(340, y),
                arrowprops=dict(arrowstyle='->', lw=1.2,
                                color=RED if i in changed else GRAY))
    if i in changed:
        ax.text(365, y + 16, '改写', ha='center', va='bottom', fontsize=9,
                color=RED, path_effects=WHITE_STROKE)
    y -= 46 * nlines + 14
ax.text(20, y - 6, "其余指令原样转发", ha='left', va='center', fontsize=10,
        color=GRAY)

# ---------- 4. ②③ 两栏路径（同一比例，共用坐标系） ----------
A, B, C = (100, 100), (200, 200), (500, 500)   # 例程三点（均在对角线上）
D, E = (300, 300), (400, 400)                  # curveTo 的两个控制点
OFF = (-10, 10)                    # closePath 闭合边的显示偏移（⊥对角线）


def T(p, dx):
    return (p[0] + dx, p[1])


def rot_label(x, y, s, color):
    """沿对角线方向的标注文字（旋转 45°）"""
    ax.text(x, y, s, ha='center', va='center', rotation=45, fontsize=10.5,
            color=color, path_effects=WHITE_STROKE, zorder=6)


def draw_path_panel(dx, filtered, title):
    """画一栏路径：dx 为整体平移量，filtered=True 画过滤后的结果"""
    ax.text(500 + dx, 590, title, ha='center', va='bottom', fontsize=13.5,
            fontweight='bold', path_effects=WHITE_STROKE)
    if not filtered:
        # lineTo 段：起点 → (200, 200)，正常连接成线
        ax.plot(*zip(T(A, dx), T(B, dx)), color=BLACK, linewidth=2.2,
                zorder=3)
        rot_label(173 + dx, 118, "lineTo 段", BLACK)
        ax.plot(*zip(T(A, dx), T(B, dx)), 'o', ms=4, color=BLACK, zorder=4)
        ax.text(90 + dx, 80, "(100, 100) moveTo", ha='right', va='top',
                fontsize=10, path_effects=WHITE_STROKE, zorder=6)
        ax.text(185 + dx, 215, "(200, 200) lineTo", ha='right', va='bottom',
                fontsize=10, path_effects=WHITE_STROKE, zorder=6)
    else:
        # lineTo 段已被改写为 moveTo：该段不再绘制（灰虚线标示消失段）
        ax.plot(*zip(T(A, dx), T(B, dx)), color=GHOST, linestyle='--',
                linewidth=1.2, zorder=2)
        rot_label(183 + dx, 108, "lineTo 段（未绘制）", GHOST)
        # (100, 100) 处留下空轮廓；(200, 200) 成为新的轮廓起点
        ax.plot(*T(A, dx), 'o', ms=6, mfc='white', mec=RED, mew=1.3,
                zorder=4)
        ax.text(90 + dx, 80, "(100, 100) moveTo（空轮廓）", ha='right',
                va='top', fontsize=10, color=RED,
                path_effects=WHITE_STROKE, zorder=6)
        ax.plot(*T(B, dx), 'o', ms=4.5, color=RED, zorder=4)
        ax.text(185 + dx, 218, "(200, 200) moveTo（原 lineTo）",
                ha='right', va='bottom', fontsize=10, color=RED,
                path_effects=WHITE_STROKE, zorder=6)
    # curveTo 段：两栏相同（控制点恰在对角线上，退化为直线）
    ax.plot(*zip(T(B, dx), T(C, dx)), color=BLUE, linewidth=2.2, zorder=3)
    ax.plot(*zip(T(B, dx), T(D, dx)), color=BLUE, linestyle=':',
            linewidth=0.9, zorder=3)
    ax.plot(*zip(T(E, dx), T(C, dx)), color=BLUE, linestyle=':',
            linewidth=0.9, zorder=3)
    ax.plot(*zip(T(D, dx), T(E, dx)), 'o', ms=4.5, mfc='white', mec=BLUE,
            mew=1.2, linestyle='none', zorder=4)
    rot_label(383 + dx, 318, "curveTo 段（控制点共线）", BLUE)
    ax.plot(*T(C, dx), 'o', ms=4, color=BLACK, zorder=4)
    ax.text(485 + dx, 522, "(500, 500)", ha='right', va='bottom',
            fontsize=10, path_effects=WHITE_STROKE, zorder=6)
    # closePath 闭合边（偏移显示）：过滤前回到起点，过滤后回到 (200, 200)
    target = B if filtered else A
    ax.plot(*zip((C[0] + OFF[0] + dx, C[1] + OFF[1]),
                 (target[0] + OFF[0] + dx, target[1] + OFF[1])),
            color=BLACK, linestyle='--', linewidth=1.1, zorder=2)
    if filtered:
        rot_label(330 + dx, 368, "closePath → 闭合到 (200, 200)", BLACK)
    else:
        rot_label(277 + dx, 325, "closePath 闭合边", BLACK)


draw_path_panel(700, False, "② 若不过滤：lineTo 正常连接成线")
draw_path_panel(1260, True, "③ 过滤后：RecordingPen 记录")

# ---------- 5. 底部图例带 ----------
ly1, ly2 = -70, -130
lx = [20, 420, 860]
ax.plot(lx[0], ly1, 'o', ms=4, color=BLACK)
ax.text(lx[0] + 22, ly1, '路径顶点（线上点）', va='center', fontsize=11)
ax.plot(lx[1], ly1, 'o', ms=4.5, mfc='white', mec=BLUE, mew=1.2)
ax.text(lx[1] + 22, ly1, 'curveTo 控制点（恰在对角线上）', va='center',
        fontsize=11, color=BLUE)
ax.plot(lx[2], ly1, 'o', ms=5, mfc='white', mec=RED, mew=1.2)
ax.text(lx[2] + 22, ly1, '空轮廓起点（moveTo 未绘制）', va='center',
        fontsize=11, color=RED)
ax.plot([lx[0] - 14, lx[0] + 14], [ly2, ly2], color=BLACK, linestyle='--',
        linewidth=1.1)
ax.text(lx[0] + 22, ly2, 'closePath 闭合边（偏移显示）', va='center',
        fontsize=11)
ax.plot([lx[1] - 14, lx[1] + 14], [ly2, ly2], color=GHOST, linestyle='--',
        linewidth=1.2)
ax.text(lx[1] + 22, ly2, '被改写后未绘制的 lineTo 段', va='center',
        fontsize=11, color=GRAY)
ax.text(lx[2] + 22, ly2, '红色 = 被过滤器改写的指令', va='center',
        fontsize=11, color=RED)

# ---------- 6. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('filterpen示意图.png', dpi=200)
fig.savefig('filterpen示意图.pdf')
print('已生成 filterpen示意图.png 与 filterpen示意图.pdf（21:9）')
