# -*- coding: utf-8 -*-
"""
实验4：字形的基线计算
读取字体级垂直度量字段（OS/2 表、hhea 表），
并用 BoundsPen 实测各参考线对应的字形轮廓位置，两者互相印证。
"""
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

font = TTFont("SourceHanSerifCN-Regular-1.otf")  # 加载思源宋体字库
glyphSet = font.getGlyphSet()          # 获取字形集
cmap = font.getBestCmap()              # 最佳字符映射表（Unicode 码点 → 字形名）
unitsPerEm = font['head'].unitsPerEm   # 每 em 包含的字体单位数

# ---------- 1. 字体级垂直度量：OS/2 表与 hhea 表 ----------
os2, hhea = font['OS/2'], font['hhea']
print("【字体级度量】基线为原点，单位是字体单位（1 em =", unitsPerEm, "）")
print("OS/2.usWinAscent  =", os2.usWinAscent)   # Win 上界
print("OS/2.usWinDescent =", os2.usWinDescent)  # Win 下界
print("Win 行高 = usWinAscent + usWinDescent =", os2.usWinAscent + os2.usWinDescent)
print("OS/2.sTypoAscender / sTypoDescender =", os2.sTypoAscender, os2.sTypoDescender)
print("hhea.ascent / descent =", hhea.ascent, hhea.descent)  # hhea 表行高字段
print("OS/2.sxHeight   =", os2.sxHeight)     # 字体声明的 x 高度
print("OS/2.sCapHeight =", os2.sCapHeight)   # 字体声明的大写高度

# ---------- 2. 字形级参考线：用 BoundsPen 实测 ----------
def measure(ch):
    """实测字符 ch 的轮廓边界框，返回 (顶端, 底端)，基线为 y=0"""
    pen = BoundsPen(glyphSet)
    glyphSet[cmap[ord(ch)]].draw(pen)
    xmin, ymin, xmax, ymax = pen.bounds
    return ymax, ymin

print("\n【字形级实测】参考线与字符轮廓顶点/底点的关系")
samples = [('h', '上升线'), ('H', '大写高度线'), ('x', 'x 高度线'),
           ('g', '下降线'), ('y', '下降线'), ('汉', '汉字稳坐基线之上')]
for ch, name in samples:
    top, bottom = measure(ch)
    print(f"'{ch}'（{name}）: 顶端 = {top}, 底端 = {bottom}")

# ---------- 3. 互相印证：Win 边界按什么口径统计 ----------
# OpenType 规范约定：usWinAscent / usWinDescent 统计的是
# Windows ANSI 字符集（cp1252）内字符的字形极值，而不是全部字形
ansi_cps = set()
for b in range(256):
    try:
        ansi_cps.add(ord(bytes([b]).decode('cp1252')))
    except UnicodeDecodeError:
        pass                       # 跳过 cp1252 中的未定义位置

def extremes(glyphNames):
    """实测一组字形的轮廓极值，返回 (最高点, 最低点)"""
    top, bottom = float('-inf'), float('inf')
    for name in glyphNames:
        pen = BoundsPen(glyphSet)
        glyphSet[name].draw(pen)
        if pen.bounds is None:   # 空格等无轮廓字形
            continue
        top = max(top, pen.bounds[3])
        bottom = min(bottom, pen.bounds[1])
    return top, bottom

print("\n【印证】Win 边界的统计口径")
topA, bottomA = extremes(cmap[cp] for cp in cmap.keys() & ansi_cps)
print("ANSI 字符集实测极值: 最高 =", topA, ", 最低 =", bottomA)
print("usWinAscent / usWinDescent =", os2.usWinAscent, "/", os2.usWinDescent)
topAll, bottomAll = extremes(glyphSet.keys())
print("全字库实测极值: 最高 =", topAll, ", 最低 =", bottomAll)
