# -*- coding: utf-8 -*-
"""
实验4（附图）：BoundsPen 求取字形边界点示意图的生成
对应书稿「BoundsPen求取字形边界点」一节的例程：
    boundsPen = BoundsPen(glyphSet)
    g.draw(boundsPen)
    bounds = boundsPen.bounds      # 返回 (xmin, ymin, xmax, ymax)
以字符 “é” 为例：用 BoundsPen 实测字形的笔画边界，并与字库自有参数对照——
思源黑体的 BASE 表直接记录了字身框与字面框（二者均为正方形）：
  字身框（em square）：unitsPerEm = 1000，下缘由 ideo 基线给出（-120），
                      故范围为 (0, -120) → (1000, 880)，1000 × 1000；
  字面框（ICF，Ideographic Character Face）：由 icfb / icft 基线给出，
                      横排取 y：-67 → 827，竖排取 x：53 → 947，894 × 894。
若为复合字形（isComposite() 为 True），程序还会逐部件上色并画出各部件的
边界，直观说明 BoundsPen 为什么要传入 glyphSet。
输出：边界框示意图.png（位图）与 边界框示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

font = TTFont("思源黑體ExtraLight.ttf")  # 加载思源黑体字库（TrueType 轮廓）
glyphSet = font.getGlyphSet()          # 获取字形集
cmap = font.getBestCmap()              # 最佳字符映射表（Unicode 码点 → 字形名）
char = 'é'                             # 测试字符：U+00E9
glyphName = cmap[ord(char)]
width = font['hmtx'][glyphName][0]     # 字宽（步进宽度）
upm = font['head'].unitsPerEm          # 每 em 包含的字体单位数


def read_baselines(font):
    """读取 BASE 表中的基线参数：横排坐标取自 HorizAxis，竖排取自 VertAxis。
    返回 {(轴向, 标签): 坐标}，如 {('h', 'ideo'): -120, ('v', 'icfb'): 53}"""
    out = {}
    if 'BASE' not in font:
        return out
    base = font['BASE'].table
    for axis, tag in ((base.HorizAxis, 'h'), (base.VertAxis, 'v')):
        if axis is None or axis.BaseTagList is None:
            continue
        tags = list(axis.BaseTagList.BaselineTag)
        for rec in axis.BaseScriptList.BaseScriptRecord:
            if rec.BaseScriptTag not in ('DFLT', 'hani'):
                continue
            bs = rec.BaseScript
            if not (bs.BaseValues and bs.BaseValues.BaseCoord):
                continue
            for i, coord in enumerate(bs.BaseValues.BaseCoord):
                if coord is not None:
                    out.setdefault((tag, tags[i]), coord.Coordinate)
    return out


# ---------- 0. 字库自有参数：字身框与字面框（均为正方形） ----------
bl = read_baselines(font)
emBottom = bl.get(('h', 'ideo'), font['OS/2'].sTypoDescender)  # 字身框下缘
emBox = (0, emBottom, upm, upm)                  # (x, y, 宽, 高)：1000 × 1000
icf = None                                       # 字面框 (x, y, 宽, 高)
if ('h', 'icfb') in bl and ('v', 'icfb') in bl:
    ix0, ix1 = bl[('v', 'icfb')], bl[('v', 'icft')]   # 竖排坐标 → x 向
    iy0, iy1 = bl[('h', 'icfb')], bl[('h', 'icft')]   # 横排坐标 → y 向
    icf = (ix0, iy0, ix1 - ix0, iy1 - iy0)            # 894 × 894
print(f"字身框（ideo / unitsPerEm）= {emBox[2]} × {emBox[3]}，下缘 y = {emBottom}")
if icf:
    print(f"字面框（icfb/icft）= {icf[2]} × {icf[3]}，",
          f"x: {icf[0]} → {icf[0] + icf[2]}，y: {icf[1]} → {icf[1] + icf[3]}")

# ---------- 1. 书稿例程：BoundsPen 求整体边界 ----------
g = glyphSet[glyphName]
boundsPen = BoundsPen(glyphSet)        # 创建 BoundsPen 对象，记录路径的边界
g.draw(boundsPen)                      # 把字形轮廓“绘制”到 BoundsPen
bounds = boundsPen.bounds              # 返回 (xmin, ymin, xmax, ymax)
print(f"Bounding box: {bounds}")
xMin, yMin, xMax, yMax = bounds

# ---------- 2. 拆解复合字形：各部件轮廓与各自的边界 ----------
glyfTable = font['glyf']
rawGlyph = glyfTable[glyphName]
print("isComposite():", rawGlyph.isComposite())
components = []                        # [(部件字形名, 轮廓指令, 部件边界), ...]
if rawGlyph.isComposite():
    rawGlyph.expand(glyfTable)
    for comp in rawGlyph.components:
        sub = glyphSet[comp.glyphName]
        try:
            (a, b), (c, d) = comp.transform      # 部件的缩放/旋转矩阵
        except AttributeError:
            (a, b), (c, d) = (1, 0), (0, 1)
        tr = Transform(a, b, c, d, comp.x, comp.y)  # 再叠加平移偏移
        rec = RecordingPen()
        sub.draw(TransformPen(rec, tr))          # 部件轮廓（变换后）
        bp = BoundsPen(glyphSet)
        sub.draw(TransformPen(bp, tr))           # 该部件的边界
        components.append((comp.glyphName, rec.value, bp.bounds))
        print(f"部件 {comp.glyphName}: bounds = {bp.bounds}")


def pen_value_path(value):
    """把 Pen 记录的轮廓指令转成 matplotlib 的 Path 对象（字体坐标，基线为 y=0）"""
    verts, codes = [], []
    for cmd, pts in value:
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


# ---------- 3. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
frameBottom = min(emBox[1], icf[1] if icf else emBox[1])
frameTop = max(emBox[1] + emBox[3], (icf[1] + icf[3]) if icf else 0)
Y0 = min(yMin, frameBottom) - 120      # 视图下缘（为底部尺寸标注留出空间）
Y1 = max(yMax, frameTop) + 70          # 视图上缘
XR = (Y1 - Y0) * 21 / 9                # 按 21:9 推出横向范围
X0, X1 = -160, -160 + XR
fig = plt.figure(figsize=(12.6, 5.4))  # 12.6 : 5.4 = 21 : 9
ax = fig.add_axes([0, 0, 1, 1])        # 坐标区充满整幅，保证输出严格 21:9
ax.set_xlim(X0, X1)
ax.set_ylim(Y0, Y1)
ax.set_aspect('equal')
ax.axis('off')

BLACK, GRAY = 'black', '#777777'
BLUE, RED = '#0055cc', '#cc2222'   # 字面框用蓝色；部件另用红/绿色
COMP_COLOR = [RED, '#007755', BLUE]

# ---------- 4. 字身框（em square，BASE 表 ideo）与字面框（ICF） ----------
ex, ey, ew, eh = emBox
ax.add_patch(Rectangle((ex, ey), ew, eh, fill=False, edgecolor=GRAY,
                       linewidth=1.4, zorder=1))
ax.text(ex + ew, ey + eh + 12, f'字身框（em square）{ew} × {eh}',
        ha='right', va='bottom', fontsize=13, color=GRAY,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])
if icf:
    fx, fy, fw, fh = icf
    ax.add_patch(Rectangle((fx, fy), fw, fh, fill=False, edgecolor=BLUE,
                           linewidth=1.2, zorder=1))
    ax.text(ex + ew, ey + eh - 12, f'字面框（ICF）{fw} × {fh}',
            ha='right', va='top', fontsize=13, color=BLUE,
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])

# ---------- 5. 绘制字形与各部件 ----------
if components:                       # 复合字形：逐部件上色
    for i, (name, value, cb) in enumerate(components):
        col = COMP_COLOR[i % len(COMP_COLOR)]
        ax.add_patch(PathPatch(pen_value_path(value),
                               facecolor='#e8e8e8' if i == 0 else '#f6dede',
                               edgecolor=col, linewidth=1.2, zorder=2))
        # 部件自身的边界（点线框）
        ax.add_patch(Rectangle((cb[0], cb[1]), cb[2] - cb[0], cb[3] - cb[1],
                               fill=False, edgecolor=col, linestyle=':',
                               linewidth=1.2, zorder=3))
else:                                # 简单字形：整体灰色填充
    rec = RecordingPen()
    g.draw(rec)
    ax.add_patch(PathPatch(pen_value_path(rec.value), facecolor='#e8e8e8',
                           edgecolor=BLACK, linewidth=1.2, zorder=2))

# ---------- 6. é 的笔画边界：BoundsPen 的测量结果（黑色虚线） ----------
ax.add_patch(Rectangle((xMin, yMin), xMax - xMin, yMax - yMin,
                       fill=False, edgecolor=BLACK, linestyle='--',
                       linewidth=1.2, zorder=4))
cx, cy = (xMin + xMax) / 2, (yMin + yMax) / 2     # 边界框中心
ax.text(cx, yMax + 18, f'ymax = {yMax}', ha='center', va='bottom',
        fontsize=12, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])
ax.text(xMax + 10, yMin, f'ymin = {yMin}', ha='left', va='center',
        fontsize=12, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])
ax.text(xMin - 24, cy, f'xmin = {xMin}', ha='right', va='center',
        rotation=90, fontsize=12, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])
ax.text(xMax + 24, cy, f'xmax = {xMax}', ha='left', va='center',
        rotation=90, fontsize=12, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])

# 宽、高双向箭头：边界框框住字形的最小外接矩形
# 宽度标注放在字身框下缘之外，避免与字面框下缘线重合
ax.annotate('', xy=(xMax, emBox[1] - 30), xytext=(xMin, emBox[1] - 30),
            arrowprops=dict(arrowstyle='<->', color=BLACK, lw=1.0))
ax.text(cx, emBox[1] - 42, f'宽 = xmax − xmin = {xMax - xMin}',
        ha='center', va='top', fontsize=12, color=BLACK)
ax.annotate('', xy=(xMax + 180, yMax), xytext=(xMax + 180, yMin),
            arrowprops=dict(arrowstyle='<->', color=BLACK, lw=1.0))
ax.text(xMax + 206, cy, f'高 = ymax − ymin = {yMax - yMin}',
        ha='left', va='center', rotation=90, fontsize=12, color=BLACK,
        path_effects=[pe.withStroke(linewidth=3, foreground='white')])

# 基线、原点位线与字宽线
ax.plot([X0 + 40, upm + 60], [0, 0], color='black', linestyle=(0, (12, 4)),
        linewidth=1.0, zorder=4)                  # 基线 y=0
ax.plot([0, 0], [Y0 + 30, Y1 - 30], color=BLACK, linewidth=0.8, zorder=4)
ax.plot([width, width], [Y0 + 30, Y1 - 30], color=BLACK, linestyle=':',
        linewidth=0.8, zorder=4)
ax.text(-12, Y1 - 36, 'x = 0', ha='right', va='top', rotation=90,
        fontsize=10, color=BLACK)
ax.text(-12, 10, '基线', ha='right', va='bottom', fontsize=10, color=BLACK)

# ---------- 7. 右侧信息栏：测量结果与图例 ----------
px = upm + 190                       # 信息栏起始横坐标
info = [
    f"字符 '{char}'（U+{ord(char):04X}）→ 字形 {glyphName}",
    f"组合字形 isComposite() = {rawGlyph.isComposite()}",
    f"BoundsPen.bounds = ({xMin}, {yMin}, {xMax}, {yMax})",
    f"宽 × 高 = {xMax - xMin} × {yMax - yMin}（字体单位）",
    f"字身框 ideo（em square）= {emBox[2]} × {emBox[3]}",
]
if icf:
    info.append(f"字面框 icfb / icft（ICF）= {icf[2]} × {icf[3]}")
info.append(f"字宽 advance width = {width}")
for i, line in enumerate(info):
    ax.text(px, Y1 - 60 - i * 68, line, ha='left', va='center', fontsize=13)

ly = Y1 - 60 - len(info) * 68 - 40   # 图例区起始纵坐标
ax.plot([px, px + 36], [ly, ly], color=GRAY, linewidth=1.4)
ax.text(px + 50, ly, '字身框（BASE 表 ideo）', ha='left', va='center',
        fontsize=13, color=GRAY)
ly -= 72
if icf:
    ax.plot([px, px + 36], [ly, ly], color=BLUE, linewidth=1.2)
    ax.text(px + 50, ly, '字面框（BASE 表 icfb / icft）', ha='left',
            va='center', fontsize=13, color=BLUE)
    ly -= 72
ax.plot([px, px + 36], [ly, ly], color=BLACK, linestyle='--', linewidth=1.2)
ax.text(px + 50, ly, '笔画边界 boundsPen.bounds', ha='left', va='center',
        fontsize=13)
ly -= 72
if components:
    for i, (name, _, _) in enumerate(components[:3]):
        col = COMP_COLOR[i % len(COMP_COLOR)]
        yy = ly - 72 * (i + 1)
        ax.plot([px, px + 36], [yy, yy], color=col, linestyle=':',
                linewidth=1.6)
        label = "字母 e 部件边界" if i == 0 else "尖音符 ´ 部件边界"
        ax.text(px + 50, yy, f'{label}（{name}）', ha='left',
                va='center', fontsize=13, color=col)
    ly -= 72 * min(len(components), 3)
ax.plot([px, px + 36], [ly - 72, ly - 72], color='black',
        linestyle=(0, (12, 4)), linewidth=1.0)
ax.text(px + 50, ly - 72, '基线 Baseline（y = 0）', ha='left', va='center',
        fontsize=13)
ax.plot([px, px + 36], [ly - 144, ly - 144], color=BLACK, linestyle=':',
        linewidth=0.8)
ax.text(px + 50, ly - 144, f'字宽线 x = {width}', ha='left', va='center',
        fontsize=13)

# ---------- 8. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('边界框示意图.png', dpi=200)
fig.savefig('边界框示意图.pdf')
print('已生成 边界框示意图.png 与 边界框示意图.pdf（21:9）')
