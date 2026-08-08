# -*- coding: utf-8 -*-
"""
实验4（附图）：SVGPathPen 字形 SVG 转化示意图的生成
对应书稿「svgPathPen字形SVG转化」一节的例程（lst:svgpathpen1）：
    pen = SVGPathPen(glyphSet)
    glyph.draw(pen)                # 绘制命令被逐条翻译成 SVG 路径指令
    svg_path = pen.getCommands()   # 拼好的 d 属性字符串
SVGPathPen 的命令级翻译规则：moveTo/lineTo/curveTo/qCurveTo/closePath
分别转为 M/L/C/Q/Z，水平和垂直线段进一步优化为 H、V 指令。
以思源黑体的字符 “瑞” 为例，分三栏可视化转化过程：
  ① 字体坐标系：轮廓与基线，y 轴向上；
  ② pen.getCommands()：返回的 SVG 指令流（拆分显示，完整字符串无
     分隔符），H、V 指令以蓝色标出；
  ③ SVG 视口渲染：y 轴向下，路径经 scale(1,-1) 翻转后正立显示，
     viewBox 起点取 (xmin, -ymax)；下方为写入文件的 XML 骨架。
所有指令与坐标均由 SVGPathPen / BoundsPen 真实计算。
输出：svgpathpen示意图.png（位图）与 svgpathpen示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
import re
from collections import Counter
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
char = '瑞'                                # 书稿例程所用字符
glyph = glyphSet[cmap[ord(char)]]

# ---------- 1. 真实执行书稿例程 ----------
pen = SVGPathPen(glyphSet)
glyph.draw(pen)                            # 路径命令 → SVG 指令
svg_path = pen.getCommands()               # d 属性字符串
boundsPen = BoundsPen(glyphSet)
glyph.draw(boundsPen)
xmin, ymin, xmax, ymax = boundsPen.bounds
# 拆分指令（在命令字母前切分；完整字符串本身无分隔符）
cmds = [c for c in re.split(r'(?=[MLHVQCZ])', svg_path) if c]
n_cmds = len(cmds)
print(f"字符 '{char}'：SVG 指令 {n_cmds} 条，",
      dict(Counter(c[0] for c in cmds)))
print(f"d 字符串共 {len(svg_path)} 字符；bounds = {boundsPen.bounds}")

# ---------- 2. 轮廓 → matplotlib Path（供 ①③ 两栏绘制） ----------
rec = RecordingPen()
glyph.draw(rec)


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
FILL = '#dcebfb'
WHITE_STROKE = [pe.withStroke(linewidth=3, foreground='white')]
# 命令字母配色：M 新轮廓 / L 直线 / H、V 水平垂直线 / Q 二次曲线 / Z 闭合
CMD_COLOR = {'M': GREEN, 'L': BLACK, 'H': BLUE, 'V': BLUE,
             'Q': RED, 'C': RED, 'Z': GRAY}

CX1, CX2, CX3 = 300, 972, 1650           # 三栏中心
CY = 390                                 # 字形区中心高度
S = min(400 / (xmax - xmin), 380 / (ymax - ymin))   # ①③ 共用同一比例
DY = CY - (ymin + ymax) / 2 * S          # 两栏共用纵向位置


def T_factory(dx):
    return lambda p: (p[0] * S + dx, p[1] * S + DY)


# ---------- 4. ① 字体坐标系（y 向上） ----------
DX1 = CX1 - (xmin + xmax) / 2 * S
T1 = T_factory(DX1)
ax.text(CX1, 608, "① 字体坐标系（y 向上）", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
path1 = value_to_path(rec.value, T1)
ax.add_patch(PathPatch(path1, fc=FILL, ec='none', zorder=2))
ax.add_patch(PathPatch(path1, fc='none', ec=BLACK, lw=1.5, zorder=3))
# 基线 y = 0
gx0, gx1 = T1((xmin, 0))[0] - 30, T1((xmax, 0))[0] + 30
ax.plot([gx0, gx1], [T1((0, 0))[1]] * 2, color=GRAY, linewidth=1, zorder=2)
ax.text(gx1, T1((0, 0))[1] - 16, "基线 y = 0", ha='right', va='top',
        fontsize=10.5, color=GRAY, path_effects=WHITE_STROKE)
# y 轴向上箭头
ax.annotate('', xy=(60, 470), xytext=(60, 300),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14))
ax.text(60, 495, "y 向上", ha='center', va='bottom', fontsize=11,
        color=BLUE, path_effects=WHITE_STROKE)

# ①→② 箭头
ax.annotate('', xy=(635, 400), xytext=(545, 400),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(590, 432, "glyph.draw(pen)", ha='center', va='center',
        fontsize=11, color='#333333', path_effects=WHITE_STROKE)

# ---------- 5. ② pen.getCommands()：SVG 指令流 ----------
ax.text(CX2, 608, "② pen.getCommands()：SVG 路径指令", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
frame = FancyBboxPatch((650, 15), 645, 530, boxstyle="round,pad=10",
                       fc='#f8f8f8', ec='#cccccc', lw=1, zorder=0)
ax.add_patch(frame)
# 完整字符串预览（无分隔符，截断显示）
preview = f'd="{svg_path[:38]}…"'
ax.text(672, 505, preview, ha='left', va='center', fontsize=9.5,
        family='monospace', color='#333333', zorder=3)
ax.text(672, 465, f"拆分指令（共 {n_cmds} 条）：", ha='left', va='center',
        fontsize=10.5, color=GRAY, zorder=3)
N_SHOW = 11
for i, tok in enumerate(cmds[:N_SHOW]):
    ax.text(672, 425 - i * 36, f"{i:2d}  {tok}", ha='left', va='center',
            fontsize=10, family='monospace',
            color=CMD_COLOR.get(tok[0], BLACK), zorder=3)
ax.text(672, 425 - N_SHOW * 36,
        f"…… 共 {n_cmds} 条，拼成 {len(svg_path)} 字符的 d 字符串",
        ha='left', va='center', fontsize=10, color=GRAY, zorder=3)

# ②→③ 箭头
ax.annotate('', xy=(1445, 400), xytext=(1325, 400),
            arrowprops=dict(arrowstyle='-|>', lw=2.2, color='#555555',
                            mutation_scale=22))
ax.text(1385, 432, "scale(1,-1) 翻转", ha='center', va='center',
        fontsize=11, color='#333333', path_effects=WHITE_STROKE)

# ---------- 6. ③ SVG 视口渲染（y 向下） ----------
DX3 = CX3 - (xmin + xmax) / 2 * S
T3 = T_factory(DX3)
ax.text(CX3, 608, "③ SVG 视口渲染（y 向下）", ha='center', va='bottom',
        fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)
# 视口（viewBox 范围）：Rectangle 的 y 起点为视口底边
vx, vy = T3((xmin, ymin))
vw, vh = (xmax - xmin) * S, (ymax - ymin) * S
ax.add_patch(Rectangle((vx, vy), vw, vh, fc='white', ec=BLACK, lw=1.5,
                       zorder=2))
path3 = value_to_path(rec.value, T3)
ax.add_patch(PathPatch(path3, fc=FILL, ec='none', zorder=3))
ax.add_patch(PathPatch(path3, fc='none', ec=BLACK, lw=1.5, zorder=4))
# viewBox 角点坐标（SVG 用户单位，标注在视口内角）
ax.text(vx + 10, vy + vh - 10, f"({xmin}, {-ymax})", ha='left', va='top',
        fontsize=10, color=GRAY, path_effects=WHITE_STROKE, zorder=5)
ax.text(vx + vw - 10, vy + 10, f"({xmax}, {-ymin})", ha='right',
        va='bottom', fontsize=10, color=GRAY,
        path_effects=WHITE_STROKE, zorder=5)
# y 轴向下箭头
ax.annotate('', xy=(vx + vw + 26, vy + 160), xytext=(vx + vw + 26,
                                                     vy + 300),
            arrowprops=dict(arrowstyle='-|>', lw=1.6, color=BLUE,
                            mutation_scale=14))
ax.text(vx + vw + 40, vy + 230, "y 向下", ha='left', va='center',
        fontsize=11, color=BLUE, path_effects=WHITE_STROKE)
# 写入文件的 XML 骨架
box = FancyBboxPatch((CX3 - 230, 20), 460, 130, boxstyle="round,pad=8",
                     fc='#f8f8f8', ec='#cccccc', lw=1, zorder=2)
ax.add_patch(box)
xml_lines = [f'<svg viewBox="{xmin} {-ymax} {xmax - xmin} {ymax - ymin}">',
             '<path d="…" transform="scale(1,-1)"/>',
             '</svg>']
for i, line in enumerate(xml_lines):
    ax.text(CX3 - 212, 120 - i * 34, line, ha='left', va='center',
            fontsize=9.5, family='monospace', zorder=3)

# ---------- 7. 底部图例带 ----------
ly1, ly2 = -85, -140
for x, letter, label in [(20, 'M', '= moveTo（新轮廓）'),
                         (300, 'L', '= lineTo（直线）'),
                         (620, 'H V', '= 水平/垂直线（lineTo 优化）'),
                         (1120, 'Q', '= qCurveTo（二次曲线）'),
                         (1480, 'Z', '= closePath（闭合）')]:
    col = CMD_COLOR[letter[0]]
    ax.text(x, ly1, letter, ha='left', va='center', fontsize=11,
            family='monospace', fontweight='bold', color=col)
    ax.text(x + 18 * len(letter) + 8, ly1, label, ha='left', va='center',
            fontsize=11)
ax.text(20, ly2, 'SVG 视口 y 轴向下：路径写入文档时需 scale(1,-1) 翻转，'
        'viewBox 起点取 (xmin, -ymax)', va='center', fontsize=11,
        color='#444444')

# ---------- 8. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('svgpathpen示意图.png', dpi=200)
fig.savefig('svgpathpen示意图.pdf')
print('已生成 svgpathpen示意图.png 与 svgpathpen示意图.pdf（21:9）')
