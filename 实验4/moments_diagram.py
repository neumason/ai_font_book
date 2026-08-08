# -*- coding: utf-8 -*-
"""
实验4（附图）：MomentsPen 求解字形图像 Hu 矩特征示意图的生成
对应书稿「MomentsPen求解字形图像Hu矩特征」一节的例程（lst:example121216）：
    momentsPen = MomentsPen(glyphSet)
    glyph.draw(momentsPen)
    area     = momentsPen.area      # M00：面积（总质量）
    momentX  = momentsPen.momentX   # M10：一阶矩 → 质心 x 坐标
    momentYY = momentsPen.momentYY  # M02：二阶矩，Y 方向扩展
以思源宋体字符 “虎” 为例，分三栏形象展示各阶矩的几何意义与 Hu 不变矩：
  ① 原字形：把轮廓看作均匀薄板——红十字为质心 (M10/M00, M01/M00)，
     蓝色等效惯性椭圆（半轴 2√λ，λ 为二阶中心矩 a、c 的特征值）与
     主轴方向 θ = ½·arctan(2b/(a−c))；
  ② 同一字形旋转 30° + 缩放 0.6 + 平移：质心、椭圆、主轴都随之改变，
     普通矩（M00、质心、θ）全部变化；
  ③ 数据对照：由二阶中心矩构成的 Hu 不变矩 φ1 = η20+η02、
     φ2 = (η20−η02)²+4η11² 在平移·旋转·缩放下保持不变（实测小数点
     后 10 位一致）——这正是 Hu 矩作为形状特征的核心价值。
  ※ φ1、φ2 只含二阶矩；φ3…φ7 还需三阶矩，超出 MomentsPen 的范围。
输出：moments示意图.png（位图）与 moments示意图.pdf（矢量图），21:9 画幅
"""
from fontTools.ttLib import TTFont
from fontTools.pens.momentsPen import MomentsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Arc
import matplotlib.patheffects as pe

# 英文与数字用 Times New Roman，中文回退到黑体；避免负号乱码
plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

ROT, SCALE = 30, 0.6                       # ②栏的变换：旋转角（度）与缩放
font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 思源宋体（CFF 三次轮廓）
glyphSet = font.getGlyphSet()
cmap = font.getBestCmap()
char = '虎'                                # 测试字符（与书稿例程一致）
glyphName = cmap[ord(char)]
g = glyphSet[glyphName]
TF = Transform().scale(SCALE).rotate(math.radians(ROT))


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
        elif op[0] == 'closePath':
            codes.append(Path.CLOSEPOLY); verts.append((0, 0))
    return Path(verts, codes)


def glyph_ops(glyph, tf=None):
    """记录字形轮廓；tf 非 None 时先经 TransformPen 变换"""
    rec = RecordingPen()
    glyph.draw(TransformPen(rec, tf) if tf else rec)
    return recording_to_ops(rec.value)


def moments_of(ops):
    """把轮廓指令重放到 MomentsPen，返回各阶矩与派生量"""
    mp = MomentsPen(glyphSet)
    for op in ops:
        if op[0] == 'moveTo':
            mp.moveTo(op[1])
        elif op[0] == 'lineTo':
            mp.lineTo(op[1])
        elif op[0] == 'curveTo':
            mp.curveTo(op[1], op[2], op[3])
        elif op[0] == 'closePath':
            mp.closePath()
    M00 = mp.area                          # M00：面积
    xc, yc = mp.momentX / M00, mp.momentY / M00     # 质心
    a = mp.momentXX / M00 - xc * xc        # 二阶中心矩（书稿公式）
    b = mp.momentXY / M00 - xc * yc
    c = mp.momentYY / M00 - yc * yc
    theta = math.degrees(0.5 * math.atan2(2 * b, a - c))  # 主轴方向
    eta20, eta02, eta11 = a / M00, c / M00, b / M00       # 归一化中心矩
    phi1 = eta20 + eta02                   # Hu 不变矩 φ1
    phi2 = (eta20 - eta02) ** 2 + 4 * eta11 ** 2          # Hu 不变矩 φ2
    lam, vec = np.linalg.eigh([[a, b], [b, c]])           # 协方差特征分解
    return dict(M00=M00, xc=xc, yc=yc, a=a, b=b, c=c, theta=theta,
                phi1=phi1, phi2=phi2, lam=lam, vec=vec)


# ---------- 1. 例程实测：原字形 vs 旋转+缩放+平移 ----------
ops0 = glyph_ops(g)
ops1 = glyph_ops(g, TF)
m0 = moments_of(ops0)
m1 = moments_of(ops1)
print(f"字符 '{char}'（U+{ord(char):04X}）→ 字形 {glyphName}")
for tag, m in (("原字形", m0), (f"旋转{ROT}°+缩放{SCALE}", m1)):
    print(f"  {tag}: M00={m['M00']:.0f} 质心=({m['xc']:.1f}, {m['yc']:.1f}) "
          f"θ={m['theta']:.2f}°")
print(f"  φ1: {m0['phi1']:.10f} vs {m1['phi1']:.10f}")
print(f"  φ2: {m0['phi2']:.10e} vs {m1['phi2']:.10e}")
assert abs(m0['phi1'] - m1['phi1']) < 1e-9 * m0['phi1']
assert abs(m0['phi2'] - m1['phi2']) < 1e-9 * m0['phi2']
print("  Hu 不变矩 φ1、φ2 实测不变（1e-9 精度内）")

allPts = [p for op in ops0 for p in op[1:]]
xMaxG = max(p[0] for p in allPts)
yMaxG = max(p[1] for p in allPts)

# ---------- 2. 画布：21:9 画幅，坐标区纵横比严格一致 ----------
Y0, Y1 = -210, 960                         # 视图纵范围（底部留图例带）
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
DX2 = 1200                                 # ②栏平移量
COLX = 1860                                # ③数据栏起始横坐标
TY = 890                                   # 栏标题高度


def draw_glyph_panel(ops, m, dx, title, title_x, show_axes):
    """画一栏字形：填充轮廓 + 质心十字 + 惯性椭圆 + 主轴与 θ 弧"""
    tr = (lambda p: (p[0] + dx, p[1]))
    path = ops_to_path([(op[0],) + tuple(tr(p) for p in op[1:])
                        if op[0] != 'closePath' else op for op in ops])
    ax.add_patch(PathPatch(path, facecolor=FILL, edgecolor=BLACK,
                           linewidth=1.1, zorder=2))
    cx, cy = m['xc'] + dx, m['yc']         # 质心
    lam, vec = m['lam'], m['vec']
    v1 = vec[:, 1]                         # 最大特征值对应的特征向量（主轴）
    v2 = vec[:, 0]
    a1, a2 = 2 * math.sqrt(lam[1]), 2 * math.sqrt(lam[0])   # 椭圆半轴 2√λ
    # 等效惯性椭圆（参数方程逐点生成）
    ts = np.linspace(0, 2 * np.pi, 200)
    ex = cx + a1 * np.cos(ts) * v1[0] + a2 * np.sin(ts) * v2[0]
    ey = cy + a1 * np.cos(ts) * v1[1] + a2 * np.sin(ts) * v2[1]
    ax.plot(ex, ey, color=BLUE, linewidth=1.2, zorder=3)
    # 主轴（实线）与副轴（点线）
    ax.plot([cx - (a1 + 40) * v1[0], cx + (a1 + 40) * v1[0]],
            [cy - (a1 + 40) * v1[1], cy + (a1 + 40) * v1[1]],
            color=BLUE, linewidth=0.9, zorder=3)
    ax.plot([cx - (a2 + 25) * v2[0], cx + (a2 + 25) * v2[0]],
            [cy - (a2 + 25) * v2[1], cy + (a2 + 25) * v2[1]],
            color=BLUE, linestyle=':', linewidth=0.9, zorder=3)
    # θ 弧（自 +x 方向到主轴）
    ax.add_patch(Arc((cx, cy), 300, 300, theta1=0, theta2=m['theta'],
                     color=BLUE, linewidth=1.0, zorder=3))
    am = math.radians(m['theta'] / 2)
    ax.text(cx + 210 * math.cos(am), cy + 210 * math.sin(am),
            f"θ={m['theta']:.1f}°", ha='left', va='center', fontsize=10.5,
            color=BLUE, path_effects=WHITE_STROKE, zorder=6)
    # 质心十字
    ax.plot([cx - 26, cx + 26], [cy, cy], color=RED, linewidth=1.6, zorder=5)
    ax.plot([cx, cx], [cy - 26, cy + 26], color=RED, linewidth=1.6, zorder=5)
    ax.text(cx + 34, cy - 10, f"质心 ({m['xc']:.1f}, {m['yc']:.1f})",
            ha='left', va='top', fontsize=10.5, color=RED,
            path_effects=WHITE_STROKE, zorder=6)
    if show_axes:                          # 基线与 x=0
        ax.plot([X0 + 20, xMaxG + 80], [0, 0], color=BLACK,
                linestyle=(0, (12, 4)), linewidth=0.9, zorder=1)
        ax.plot([0, 0], [Y0 + 200, yMaxG + 20], color=BLACK, linewidth=0.7,
                zorder=1)
        ax.text(X0 + 26, 8, '基线 y = 0', ha='left', va='bottom',
                fontsize=9.5, color=BLACK, path_effects=WHITE_STROKE)
    else:                                  # 变换后的原基线方向（斜线）
        k = math.tan(math.radians(ROT))
        ax.plot([dx - 260, dx + 700], [-260 * k, 700 * k], color=GRAY,
                linestyle=(0, (12, 4)), linewidth=0.8, zorder=1)
        ax.text(dx + 706, 700 * k, '原基线方向', ha='left', va='center',
                fontsize=9, color=GRAY, path_effects=WHITE_STROKE)
    ax.text(title_x, TY, title, ha='center', va='bottom',
            fontsize=13.5, fontweight='bold', path_effects=WHITE_STROKE)


draw_glyph_panel(ops0, m0, 0, "① 原字形：质心与惯性椭圆", 500, True)
draw_glyph_panel(ops1, m1, DX2, f"② 旋转 {ROT}° + 缩放 {SCALE} 后", 1350,
                 False)

# ---------- 3. ③ 数据栏：矩值对照 ----------
ax.text(COLX + 220, TY, "③ 矩值对照（原 → 变换后）", ha='center',
        va='bottom', fontsize=13.5, fontweight='bold',
        path_effects=WHITE_STROKE)
MONO = 'monospace'
pairs = [
    ("M00（面积）", f"{m0['M00']:,.0f}", f"{m1['M00']:,.0f}", False),
    ("质心 xc", f"{m0['xc']:.1f}", f"{m1['xc']:.1f}", False),
    ("质心 yc", f"{m0['yc']:.1f}", f"{m1['yc']:.1f}", False),
    ("主轴 θ", f"{m0['theta']:.1f}°", f"{m1['theta']:.1f}°", False),
    ("Hu φ1", f"{m0['phi1']:.10f}", "相同", True),
    ("Hu φ2", f"{m0['phi2']:.4e}", "相同", True),
]
yy = 800
for label, v0, v1, same in pairs:
    ax.text(COLX, yy, label, ha='left', va='center', fontsize=11.5)
    ax.text(COLX + 210, yy, v0, ha='left', va='center', fontsize=11,
            family=MONO)
    ax.text(COLX + 450, yy, "→", ha='left', va='center', fontsize=11,
            color=GRAY)
    ax.text(COLX + 490, yy, v1, ha='left', va='center', fontsize=11,
            family=MONO if not same else plt.rcParams['font.family'],
            color=RED if same else BLACK)
    yy -= 56
ax.text(COLX, yy - 10, "φ1、φ2 由二阶中心矩构成，平移·旋转·缩放下不变",
        ha='left', va='center', fontsize=10, color=GRAY)

# ---------- 4. 底部图例带 ----------
ly = -150
lx = [20, 480, 980, 1250]
ax.plot([lx[0] - 12, lx[0] + 12], [ly, ly], color=RED, linewidth=1.6)
ax.plot([lx[0], lx[0]], [ly - 12, ly + 12], color=RED, linewidth=1.6)
ax.text(lx[0] + 26, ly, '质心 (M10/M00, M01/M00)', va='center', fontsize=11)
from matplotlib.patches import Ellipse
ax.add_patch(Ellipse((lx[1], ly), 44, 26, angle=20, fill=False,
                     edgecolor=BLUE, linewidth=1.2))
ax.text(lx[1] + 34, ly, '等效惯性椭圆（半轴 2√λ）', va='center', fontsize=11,
        color=BLUE)
ax.plot([lx[2] - 14, lx[2] + 14], [ly - 8, ly + 8], color=BLUE, linewidth=0.9)
ax.text(lx[2] + 26, ly, '主轴方向 θ', va='center',
        fontsize=11, color=BLUE)
ax.plot([lx[3] - 14, lx[3] + 14], [ly, ly], color=BLACK,
        linestyle=(0, (12, 4)), linewidth=0.9)
ax.text(lx[3] + 26, ly, '基线 y = 0', va='center', fontsize=11)

# ---------- 5. 输出（坐标区充满整幅，成图严格 21:9） ----------
fig.savefig('moments示意图.png', dpi=200)
fig.savefig('moments示意图.pdf')
print('已生成 moments示意图.png 与 moments示意图.pdf（21:9）')
