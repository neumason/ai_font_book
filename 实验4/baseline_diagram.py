# -*- coding: utf-8 -*-
"""
实验4（附图）：基线参考线示意图的生成
在 baseline_metrics.py 的基础上，把 h、H、x、g、y、汉 六个字形轮廓
直接绘制成图，并按读取/实测的高度画出各类基线参考线。
输出：基线示意图.png（位图）与 基线示意图.pdf（矢量图）
"""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

# 避免中文与负号乱码
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 加载思源宋体字库
glyphSet = font.getGlyphSet()          # 获取字形集
cmap = font.getBestCmap()              # 最佳字符映射表（Unicode 码点 → 字形名）
os2 = font['OS/2']


def glyph_path(glyph):
    """把一个字形轮廓转成 matplotlib 的 Path 对象（字体坐标，基线为 y=0）"""
    pen = RecordingPen()
    glyph.draw(pen)
    verts, codes = [], []
    for cmd, pts in pen.value:
        if cmd == "moveTo":
            codes.append(Path.MOVETO)
            verts.append(pts[0])
        elif cmd == "lineTo":
            codes.append(Path.LINETO)
            verts.append(pts[0])
        elif cmd == "curveTo":          # 三次贝塞尔（CFF 轮廓）
            codes += [Path.CURVE4, Path.CURVE4, Path.CURVE4]
            verts += list(pts)
        elif cmd == "qCurveTo":         # 二次贝塞尔（TrueType 轮廓）
            pts = list(pts)
            for i in range(len(pts) - 1):
                codes += [Path.CURVE3, Path.CURVE3]
                verts += [pts[i], pts[i + 1]]
        elif cmd == "closePath":
            codes.append(Path.CLOSEPOLY)
            verts.append((0, 0))
    return Path(verts, codes)


def measure_top_bottom(ch):
    """实测字符 ch 的轮廓顶端与底端（基线为 y=0）"""
    pen = BoundsPen(glyphSet)
    glyphSet[cmap[ord(ch)]].draw(pen)
    xmin, ymin, xmax, ymax = pen.bounds
    return ymax, ymin


# ---------- 1. 确定各类参考线的高度 ----------
chars = ['H', 'x', 'g', 'y', '汉']        # 参与展示的字形
lines = [                                 # (高度, 中文名, 英文名, 颜色, 线型, 线宽)
    (os2.usWinAscent,          'Win 上界', 'usWinAscent', '#000000', (0, (2, 2)), 0.9),
    (measure_top_bottom('h')[0], '上升线',  'Ascender',   '#000000', (0, (6, 3)), 0.9),
    (os2.sCapHeight,           '大写高度线', 'Cap height', '#000000', (0, (6, 3)), 0.9),
    (os2.sxHeight,             'x 高度线',  'x-height',   '#000000', (0, (6, 3)), 0.9),
    (0,                        '基线',     'Baseline',    '#000000', (0, (12, 4)), 1.0),
    (min(measure_top_bottom('g')[1], measure_top_bottom('y')[1]),
                               '下降线',   'Descender',   '#000000', (0, (6, 3)), 0.9),
    (-os2.usWinDescent,        'Win 下界', 'usWinDescent', '#000000', (0, (2, 2)), 0.9),
]

# ---------- 2. 绘制字形轮廓 ----------
fig, ax = plt.subplots(figsize=(11, 4.2))
x_cursor = 60          # 当前排版位置（字体单位）
margin = 60            # 字间额外留白
for ch in chars:
    glyph = glyphSet[cmap[ord(ch)]]
    path = glyph_path(glyph)
    path.vertices[:, 0] += x_cursor            # 横向平移到排版位置
    ax.add_patch(PathPatch(path, facecolor='black', edgecolor='none'))
    x_cursor += glyph.width + margin           # 按字宽步进
word_right = x_cursor

# ---------- 3. 绘制参考线与标注 ----------
x_left, x_right = -20, word_right + 60
min_gap = 130        # 右侧标注的最小垂直间距，防止相邻文字重叠
placed_y = None
for y, cname, ename, color, ls, lw in lines:   # lines 已按高度自上而下排列
    ax.plot([x_left, x_right], [y, y], color=color, linestyle=ls, linewidth=lw)
    label_y = y if placed_y is None else min(y, placed_y - min_gap)
    placed_y = label_y
    ax.text(x_right + 40, label_y, f'{cname} {ename} = {y}',
            va='center', ha='left', fontsize=14, color=color)

# 左侧双向箭头：Win 上下界以基线为原点测量
arrow_x = -60
ax.annotate('', xy=(arrow_x, os2.usWinAscent), xytext=(arrow_x, 0),
            arrowprops=dict(arrowstyle='<->', color='#000000', lw=1.2))
ax.text(arrow_x - 85, os2.usWinAscent / 2, 'usWinAscent',
        rotation=90, va='center', ha='center', fontsize=12, color='#000000')
ax.annotate('', xy=(arrow_x, 0), xytext=(arrow_x, -os2.usWinDescent),
            arrowprops=dict(arrowstyle='<->', color='#000000', lw=1.2))
ax.text(arrow_x - 85, -os2.usWinDescent / 2, 'usWinDescent',
        rotation=90, va='center', ha='center', fontsize=12, color='#000000')

# ---------- 4. 坐标与输出 ----------
ax.set_xlim(x_left - 280, x_right + 900)
ax.set_ylim(-os2.usWinDescent - 180, os2.usWinAscent + 180)
ax.set_aspect('equal')
ax.axis('off')
fig.savefig('基线示意图.png', dpi=200, bbox_inches='tight')
fig.savefig('基线示意图.pdf', bbox_inches='tight')
print('已生成 基线示意图.png 与 基线示意图.pdf')
for y, cname, ename, color, ls, lw in lines:
    print(f'  {cname}（{ename}）: y = {y}')
