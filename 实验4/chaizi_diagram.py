# -*- coding: utf-8 -*-
"""
实验4（附图）：hanzi_chaizi 汉字拆字示意图的生成
对应书稿「拆字」一节的两个例程（lst:chaizi1、lst:chaizi2）。
本程序分两部分：
  第一部分即书稿例程本体——用 HanziChaizi 查询汉字部件（query 只拆一
  层，独体字返回 None，可用 default 兜底），并在 query 的基础上递归，
  把 “想” 拆成深度 2 的部件树（嵌套字典）。
  第二部分把部件树绘制成示意图：深度 0 为原字（思源宋体真实轮廓），
  第 1 层为 query 拆出的部件（相、心），第 2 层把各部件再拆一层——
  “相” 拆出 木、目 两个独体部件；“心” 无字级部件，库中记录深入笔
  画层级，拆出 丿、乚、丶、丶。到达设定深度的节点不再展开。
输出：拆字示意图.png（位图）与 拆字示意图.pdf（矢量图）
"""
from hanzi_chaizi import HanziChaizi
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ========== 第一部分：书稿例程（lst:chaizi1、lst:chaizi2） ==========
hc = HanziChaizi()                # 加载内置拆字数据（2 万余字）
for ch in ['名', '林', '想', '一']:
    print(ch, '->', hc.query(ch))
print(hc.query('一', default=['一']))


def decompose(ch, depth=2):
    """递归拆分：query 查不到部件时以字本身为叶节点"""
    if depth == 0:
        return ch
    parts = hc.query(ch)
    if not parts:                 # 独体字：不可再拆
        return ch
    return {ch: [decompose(p, depth - 1) for p in parts]}


tree = decompose('想')
print(tree)

# ========== 第二部分：绘制部件树示意图 ==========
font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 加载思源宋体字库
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()


def glyph_verts(ch):
    """把字符 ch 的字形轮廓记录为 matplotlib 可用的顶点与路径码"""
    rec = RecordingPen()
    glyphSet[cmap[ord(ch)]].draw(rec)
    verts, codes = [], []
    for cmd, pts in rec.value:
        if cmd == "moveTo":
            codes.append(Path.MOVETO)
            verts.append(pts[0])
        elif cmd == "lineTo":
            codes.append(Path.LINETO)
            verts.append(pts[0])
        elif cmd == "curveTo":               # 三次贝塞尔（CFF 轮廓）
            codes += [Path.CURVE4, Path.CURVE4, Path.CURVE4]
            verts += list(pts)
        elif cmd == "closePath":
            codes.append(Path.CLOSEPOLY)
            verts.append((0, 0))
    return np.array(verts, dtype=float), codes


# ---------- 树结构：节点 = (字符, x 列, y 位置)，边 = (父索引, 子索引) ----------
# 列：0 原字 / 1 一级部件 / 2 二级部件；y 按叶节点均布，父节点取子节点中点
COL_X = [210, 670, 1100]
LEAF_Y = [580, 480, 380, 280, 180, 80]     # 6 个叶节点的纵坐标
nodes = [                                  # (字符, 列, y, 缩放)
    ('想', 0, 380, 1.35),                  # 根节点：相、心 的中点
    ('相', 1, 530, 1.0),                   # 木、目 的中点
    ('心', 1, 230, 1.0),                   # 丿、乚、丶、丶 的中点
    ('木', 2, LEAF_Y[0], 1.0),
    ('目', 2, LEAF_Y[1], 1.0),
    ('丿', 2, LEAF_Y[2], 1.0),
    ('乚', 2, LEAF_Y[3], 1.0),
    ('丶', 2, LEAF_Y[4], 1.0),
    ('丶', 2, LEAF_Y[5], 1.0),
]
edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6), (2, 7), (2, 8)]

# ---------- 画布 ----------
W, H = 1360, 700
fig = plt.figure(figsize=(13.6, 7.0))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect('equal')
ax.axis('off')

BLACK, GRAY, BLUE = 'black', '#777777', '#0055cc'
GHOST = '#999999'
S = 0.075                                  # 字体单位 → 图单位（字形高约 68）

# 各节点的实际外接半宽（用于边的起止点）
halfw = []
for ch, col, y, k in nodes:
    v, _ = glyph_verts(ch)
    halfw.append((v[:, 0].max() - v[:, 0].min()) / 2 * S * k + 8)

# ---------- 画边（先画线，后压字形） ----------
for i, j in edges:
    ch_i, col_i, y_i, k_i = nodes[i]
    ch_j, col_j, y_j, k_j = nodes[j]
    x_i, x_j = COL_X[col_i], COL_X[col_j]
    x0, x1 = x_i + halfw[i], x_j - halfw[j]
    xm = (x0 + x1) / 2                     # 肘形连接线：先横后纵再横
    ax.plot([x0, xm, xm, x1], [y_i, y_i, y_j, y_j],
            color=GHOST, lw=1.2, zorder=1)

# ---------- 画节点字形 ----------
for (ch, col, y, k), hw in zip(nodes, halfw):
    v, codes = glyph_verts(ch)
    c = v.mean(axis=0)
    v = (v - c) * (S * k) + np.array([COL_X[col], y])
    ax.add_patch(PathPatch(Path(v, codes), facecolor=BLACK,
                           edgecolor='none', zorder=3))

# ---------- 列标题与分组标注 ----------
HEAD = ['深度 0：原字', '深度 1：部件', '深度 2：部件再拆']
for x, t in zip(COL_X, HEAD):
    ax.text(x, 665, t, ha='center', va='center', fontsize=13.5,
            fontweight='bold',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])
# “心” 的四个子节点为笔画级拆分，加竖向括注
bx = COL_X[2] + 90
ax.plot([bx, bx + 10, bx + 10, bx], [380, 380, 80, 80],
        color=BLUE, lw=1.2)
ax.text(bx + 22, 230, '“心” 无字级部件，\n库中记录深入笔画', ha='left',
        va='center', fontsize=10, color=BLUE)

# ---------- 输出 ----------
fig.savefig('拆字示意图.png', dpi=200)
fig.savefig('拆字示意图.pdf')
print('已生成 拆字示意图.png 与 拆字示意图.pdf')
