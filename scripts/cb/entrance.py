"""正面入場口(西の門)と、メインスタンドの裏の中央(大階段・英文の板・殿下の像・街灯)の細部。

資料(refs/detail、meta.json に出どころ。git に入れない):
  - Syced「Chichibunomiya Rugby Stadium (70564)」2025-01-19 CC0: 門を斜めから(柱・梁の文字・看板・引き戸・銘板・案内板・球の街灯)
  - Syced「Captain (12259)」2025-01-19 CC0: 大階段の上の像、英文の板、曲がった街灯、壁灯、ゲートの札
  - Syced「Chichibunomiya Rugby Stadium (84327)」2025-01-19 CC0: 外壁の正面、大階段、緑の仮柵、駐車の線
  - ウィ貴公子「秩父宮ラグビー場 2025年9月2日の東京 … IMG 6918」CC BY-SA 4.0: 門の正面、左の柵、閉じた引き戸、車止め
  - 「202304011520 IMG 5730」2023 CC BY-SA 4.0: 梁の文字の全体(13 文字)
  - Another Believer「… 2019 - 153」CC BY-SA 4.0: 外壁と大階段
寸法はどれも写真の比からの推定(ほかに出どころがない)。形・数・色・文字は写真で確かめたもの。
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import layout, materials as M
from .util import MB, text_obj

EN_FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"

# 梁の文字。2023・2025 年の写真 3 枚で同じ 13 文字(「立霞ヶ」の字はない。理由は資料が見つからず不明)
GATE_TEXT = "國丘競技場秩父宮ラグビー場"

G = dict(x=0.5, y=131.0, span=10.0, pillar=1.2, clear=4.7, under=0.45, lintel=1.0, depth=0.9,
         gap=0.12, board=1.9, block=1.25, band=0.1, leaf_h=2.4, leaf_open=30.0,
         fence=22.0, curb=0.35, hedge=0.7)


# ---------------------------------------------------------------- 門

def gate(c):
    x0, y0, p = G["x"], G["y"], G["pillar"]
    mb = MB()
    blk, red, plate = M.get("gate_block"), M.get("gate_red"), M.get("gate_plate")
    steel, corten = M.get("dark_steel"), M.get("corten")
    zu = G["clear"]                          # 梁の下の暗い鋼の梁の下端
    zl = zu + G["under"]                     # 名前の板の下端
    zt = zl + G["lintel"]                    # 名前の板の上端
    zb0, zb1 = zt + G["gap"], zt + G["gap"] + G["board"]   # 看板
    top = zb1 + 0.15
    xl, xr = x0 - G["span"] / 2 - p, x0 + G["span"] / 2 + p
    # 柱: 焦げ茶の四角い塊を積み、間に赤い帯(写真 70564 の右の柱、724 の左の柱)
    for sx in (-1, 1):
        cx = x0 + sx * (G["span"] / 2 + p / 2)
        z = 0.0
        k = 0
        while z < top - 1e-6:
            z1 = min(top, z + G["block"])
            w = p / 2 + (0.02 if k % 2 else 0.0)            # 塊ごとに少し太さが違う
            mb.box(cx - w, cx + w, y0 - w, y0 + w, z, z1, blk)
            if z1 < top - 1e-6:
                mb.box(cx - p / 2 + 0.03, cx + p / 2 - 0.03, y0 - p / 2 + 0.03, y0 + p / 2 - 0.03, z1, z1 + G["band"], red)
                z1 += G["band"]
            z = z1
            k += 1
    # 梁: 下の暗い鋼の梁(左の 1/3 は下へ深い)、灰色の鋼板の名前の板(3 枚の継ぎ目)、上の看板(さびた鋼板、縦の継ぎ目)
    d = G["depth"]
    mb.box(xl, xr, y0 - d / 2 + 0.15, y0 + d / 2 - 0.15, zu, zl, steel)
    xs1 = xl + (xr - xl) * 0.3
    mb.box(xl, xs1, y0 - d / 2 + 0.1, y0 + d / 2 - 0.1, zu - 0.5, zu, steel)
    for (a, b) in ((xl, xs1), (xs1, xl + (xr - xl) * 0.68), (xl + (xr - xl) * 0.68, xr)):
        mb.box(a + 0.01, b - 0.01, y0 - d / 2, y0 + d / 2, zl, zt, plate)
    mb.box(xl, xr, y0 - 0.12, y0 + 0.12, zt, zb0, steel)                 # 看板を支える枠(すき間から空が見える)
    mb.box(xl + 0.05, xr - 0.05, y0 - 0.2, y0 + 0.2, zb0, zb1, corten)
    peel = M.get("white_paint")
    n = 7
    import random
    rnd = random.Random(131)
    for i in range(1, n):
        xx = xl + (xr - xl) * i / n
        mb.box(xx - 0.015, xx + 0.015, y0 + 0.2, y0 + 0.215, zb0, zb1, steel)      # 縦の継ぎ目
        for _ in range(3):                                                    # 継ぎ目の白い塗装のはがれ
            za = rnd.uniform(zb0 + 0.1, zb1 - 0.5)
            mb.box(xx + 0.018, xx + 0.04, y0 + 0.2, y0 + 0.22, za, za + rnd.uniform(0.15, 0.45), peel)
    for zz in (zb0, zb1 - 0.06):                                              # 上下の山形鋼
        mb.box(xl, xr, y0 + 0.2, y0 + 0.27, zz, zz + 0.06, steel)
    # 引き戸: 柱の内側を軸に、内(スタジアムの側)へ開いた 2 枚。縦の平たい棒が中ほどで横にずれる(写真 724・70564)
    lh = G["leaf_h"]
    a = math.radians(G["leaf_open"])
    for sx in (-1, 1):
        hx = x0 + sx * (G["span"] / 2)
        L = G["span"] / 2 - 0.05
        dirv = Vector((-sx * math.cos(a), -math.sin(a), 0.0))
        nrm = Vector((-dirv.y, dirv.x, 0.0))
        o = Vector((hx, y0 - p / 2 + 0.15, 0.0))
        P = lambda s, z, t=0.0: o + dirv * s + nrm * t + Vector((0, 0, z))
        for zz, hh in ((0.08, 0.1), (lh - 0.1, 0.1), (lh * 0.52, 0.06)):
            mb.bar(P(0, zz + hh / 2), P(L, zz + hh / 2), 0.06, hh, steel)
        for s in (0.04, L - 0.04):
            mb.bar(P(s, 0.08), P(s, lh), 0.08, 0.08, steel)
        k = int(L / 0.2)
        for j in range(1, k):
            s = L * j / k
            mb.bar(P(s, 0.18), P(s, lh * 0.52), 0.05, 0.012, steel)
            mb.bar(P(s + 0.06, lh * 0.52 + 0.06), P(s + 0.06, lh - 0.1), 0.05, 0.012, steel)
    # 開口の中央の車止め(ステンレス)
    mb.cyl((x0, y0 - 0.2, 0.0), (x0, y0 - 0.2, 0.9), 0.06, M.get("stainless"), n=10, caps=True)
    # 両脇の柵: 低いコンクリートの縁石の上に、焦げ茶の鉄の縦棒(上は斜めに切って高さがそろわない)。道の側に植え込み
    fence = M.get("fence_brown")
    conc = M.get("concrete_light")
    hedge = M.get("hedge")
    for sx in (-1, 1):
        xa, xb = sorted((x0 + sx * (G["span"] / 2 + p), x0 + sx * (G["span"] / 2 + p + G["fence"])))
        mb.box(xa, xb, y0 - 0.2, y0 + 0.2, 0.0, G["curb"], conc)
        for zz in (G["curb"] + 0.15, G["curb"] + 1.55):
            mb.box(xa, xb, y0 - 0.04, y0 + 0.04, zz, zz + 0.05, fence)
        kk = int((xb - xa) / 0.16)
        for j in range(kk):
            xx = xa + 0.08 + (xb - xa - 0.16) * j / max(1, kk - 1)
            h = 1.85 + 0.45 * ((j * 0.618) % 1.0)
            mb.box(xx - 0.025, xx + 0.025, y0 - 0.015, y0 + 0.015, G["curb"], G["curb"] + h, fence)
        # 植え込み。道から見て右(−X)の柱の脇は銘板と案内板の所をあける
        xh0, xh1 = (xa, xb - 3.4) if sx < 0 else (xa + 0.6, xb)
        mb.box(xh0, xh1, y0 + 0.35, y0 + 1.2, 0.0, G["hedge"], hedge)
    # 道から見て右(−X)の柱の脇の銘板(金属の縦長の板に「秩父宮ラグビー場」、右上に小さく「独立行政法人日本スポーツ振興センター」、下は青緑の台)
    px = xl - 0.55
    mb.box(px - 0.38, px + 0.38, y0 + 0.25, y0 + 0.4, 0.0, 0.55, M.get("sign_teal"))
    mb.box(px - 0.36, px + 0.36, y0 + 0.27, y0 + 0.38, 0.55, 2.9, M.get("plaque_metal"))
    # 案内板(白い板に青緑の見出し)
    bx = px - 1.15
    for xx in (bx - 0.5, bx + 0.5):
        mb.box(xx - 0.04, xx + 0.04, y0 + 0.3, y0 + 0.38, 0.0, 2.7, steel)
    mb.box(bx - 0.55, bx + 0.55, y0 + 0.38, y0 + 0.42, 0.9, 2.5, M.get("sign_white"))
    mb.box(bx - 0.55, bx + 0.55, y0 + 0.42, y0 + 0.43, 2.25, 2.5, M.get("sign_teal"))
    # 球の頭の街灯(門の左右、道の側)
    glob = M.emissive("globe_lamp", (1.0, 0.92, 0.78, 1.0), 0.0, 30.0, base=M.srgb(232, 232, 226))
    for (lx, ly) in ((xr + 1.4, y0 + 0.9), (bx - 1.4, y0 + 0.9)):
        mb.cyl((lx, ly, 0.0), (lx, ly, 4.6), 0.07, M.get("white_paint"), n=10)
        _sphere(mb, Vector((lx, ly, 4.9)), 0.3, glob)
    mb.build("main_gate", c)
    # 文字: 名前の板の道の側に、焦げ茶の浮き文字(夜も光らない。写真 725)
    letters = M.get("gate_letters")
    zc = (zl + zt) / 2
    n = len(GATE_TEXT)
    xi0, xi1 = x0 - G["span"] / 2, x0 + G["span"] / 2           # 柱の内側の幅に並べる(写真では文字が柱の間いっぱい)
    w = (xi1 - xi0) * 0.94
    for i, ch in enumerate(GATE_TEXT):
        xx = xi1 - (xi1 - xi0) * 0.03 - w * (i + 0.5) / n        # 道から見て左(+X)から読む
        text_obj("gate_ch_%02d" % i, ch, 0.42, letters, c, (xx, y0 + d / 2 + 0.005, zc), (0, 1, 0), jp=True, extrude=0.02)
    # 銘板の彫った文字
    eng = M.get("text_dark")
    for i, ch in enumerate("秩父宮ラグビー場"):
        text_obj("plaque_ch_%d" % i, ch, 0.17, eng, c, (px - 0.05, y0 + 0.385, 2.55 - i * 0.24), (0, 1, 0), jp=True)
    for i, ch in enumerate("独立行政法人日本スポーツ振興センター"):
        if i > 17:
            break
        text_obj("plaque_s_%d" % i, ch, 0.06, eng, c, (px - 0.24, y0 + 0.385, 2.75 - i * 0.085), (0, 1, 0), jp=True)


# ---------------------------------------------------------------- メインの裏の中央

def facade_center(c, F):
    """英文の板の文字、殿下の像、曲がった街灯、壁灯、ゲートの札、大階段の手すり、広場の緑の仮柵。
    F は stands.FACADE(踊り場の高さ・階段の位置)。座標はメインスタンドの局所(u = X、d は外へ)で決めて、xf で直す。"""
    st = layout.stand("west")
    xf = layout.xf("west")
    d1 = st["back_block"]["d1"]
    z0 = layout.top_z(st)
    top = F["stair_steps"] * F["stair_rise"]              # 踊り場の高さ
    b0 = z0 + 0.4 - F["band_h"]
    W = lambda u, d, z: xf @ Vector((u, d, z))
    nrm = (xf.to_3x3() @ Vector((0, 1, 0))).normalized()  # 外向き
    # 英文「Prince Chichibu / Memorial Rugby Ground」: 焦げ茶の浮き文字が上に凸の弧を描く 2 行(写真 Captain 12259)
    brown = M.get("emblem_brown")
    zc = top + (b0 - top) * 0.62
    for line, (txt, h, R, zoff) in enumerate((("Prince  Chichibu", 0.36, 3.2, 0.62), ("Memorial  Rugby  Ground", 0.36, 3.7, 0.0))):
        widths = [0.22 if ch == " " else (0.36 if ch in "mMwG" else (0.16 if ch in "il" else 0.27)) for ch in txt]
        widths = [w * h / 0.36 for w in widths]
        tot = sum(widths)
        ang0 = tot / R / 2                                 # 弧の左端の角度
        acc = 0.0
        cz = zc + zoff - R                                 # 弧の中心(下)
        for i, ch in enumerate(txt):
            mid = acc + widths[i] / 2
            acc += widths[i]
            if ch == " ":
                continue
            th = ang0 - mid / R                            # 左が正の角度(中心から見て)
            u = -R * math.sin(th)                          # 外から見て左が +u … 外から見ると左右が逆なので符号を反転
            z = cz + R * math.cos(th)
            up = Vector((math.sin(th), 0.0, math.cos(th)))
            upw = (xf.to_3x3() @ up).normalized()
            text_obj("emblem_%d_%02d" % (line, i), ch, h, brown, c, W(-u, d1 - 0.19, z), nrm, extrude=0.03, up=upw, font=EN_FONT)
    # 殿下の像: ボールを右腕に抱えて立つラグビー選手(ジャージの襟、短パン、長い靴下)、赤い御影石の角錐台(写真 Captain 12259)
    us, ds = 0.0, d1 + 0.9
    sm = MB(xf)
    gran = M.get("granite_red")
    _frustum(sm, us, ds, top, 1.0, 0.9, 0.82, 0.72, 1.2, gran)
    sm.box(us - 0.33, us + 0.33, ds - 0.28, ds + 0.28, top + 1.2, top + 1.26, M.get("dark_steel"))
    sm.build("statue_base", c)
    _statue(c, xf @ Matrix.Translation((us, ds, top + 1.26)))
    # 曲がった街灯: 踊り場の両脇の腰壁から立ち、上で中央へ曲がる白い柱と円錐の笠(写真 Captain 12259・84327)
    lm = MB(xf)
    pole = M.get("lamp_pole")
    shade = M.emissive("cone_lamp", (1.0, 0.9, 0.74, 1.0), 0.0, 25.0, base=M.srgb(228, 216, 212))
    w = F["stair_w"]
    for s in (-1, 1):
        ub, db = s * (w / 2 + 2.15), d1 + F["landing"] - 1.0
        H, R = 5.2, 1.6
        lm.cyl((ub, db, top), (ub, db, top + H), 0.075, pole, n=10)
        prev = Vector((ub, db, top + H))
        for k in range(1, 9):
            t = math.radians(90.0 * k / 8)
            p = Vector((ub - s * R * (1 - math.cos(t)), db, top + H + R * math.sin(t)))
            lm.cyl(tuple(prev), tuple(p), 0.07, pole, n=10)
            prev = p
        tip = prev + Vector((-s * 0.25, 0, 0))
        lm.cyl(tuple(prev), tuple(tip), 0.07, pole, n=10)
        lm.cyl(tuple(tip + Vector((0, 0, 0.05))), tuple(tip - Vector((0, 0, 0.5))), 0.09, shade, n=14, r1=0.2, caps=True)
    # 壁灯(サーモン色の半円筒)と、ゲートの札(「← GATE 1~4」「GATE 4~7 →」)
    sal = M.get("sconce_salmon")
    step = 98.0 / 14
    for s in (-1, 1):
        uc = s * step / 2
        lm.cyl((uc + s * 0.1, d1 + 0.02, top + 2.2), (uc + s * 0.1, d1 + 0.02, top + 2.75), 0.17, sal, n=12, caps=True)
        lm.box(uc - 0.3, uc + 0.3, d1 + 0.0, d1 + 0.03, top + 1.0, top + 1.14, M.get("sign_white"))
    # 大階段の手すり(ステンレス、中央寄りに 2 本)
    stl = M.get("stainless")
    run, ns, rz = F["stair_run"], F["stair_steps"], F["stair_rise"]
    dtop = d1 + F["landing"]
    for u in (-1.6, 1.6):
        a, b = (u, dtop + 0.2, top + 0.9), (u, dtop + run - 0.2, 0.9)
        lm.cyl(a, b, 0.025, stl, n=8)
        for k in range(5):
            t = k / 4
            pd = dtop + 0.2 + (run - 0.4) * t
            pz = top * (1 - t)
            lm.cyl((u, pd, pz), (u, pd, pz + 0.9), 0.02, stl, n=8)
    lm.build("facade_center_lamps", c)
    # 1 階の上の案内(写真 84327・724): 道から見て左に青い枠の「← 1~3 ゲート」の札、右に座席表の板
    sg = MB(xf)
    sg.box(9.0, 12.6, d1 + 0.05, d1 + 0.12, top + 0.55, top + 1.25, M.get("sign_white"))
    sg.box(9.0, 12.6, d1 + 0.12, d1 + 0.13, top + 0.55, top + 0.63, M.get("sign_blue"))
    sg.box(-15.6, -12.4, d1 + 0.05, d1 + 0.12, top - 0.2, top + 1.6, M.get("sign_white"))
    sg.box(-15.3, -12.7, d1 + 0.12, d1 + 0.13, top + 0.0, top + 1.4, M.get("seatmap"))
    sg.build("facade_signs", c)
    text_obj("gate_dir_sign", "← 1~3 ゲート", 0.28, M.get("sign_blue"), c, W(10.8, d1 + 0.125, top + 0.95), nrm, jp=True)
    for s, txt in ((1, "← GATE 1~4"), (-1, "GATE 4~7 →")):
        uc = s * step / 2
        text_obj("gate_sign_%d" % s, txt, 0.07, M.get("text_dark"), c, W(uc, d1 + 0.035, top + 1.07), nrm)
    # 広場の緑の仮柵(行事の列を作る。写真 724・84327。並びは写真の日のもの)
    bm = MB()
    grn = M.get("barrier_green")
    lines = [((-22.0, 96.0), (-6.5, 96.0)), ((-22.0, 99.0), (-6.5, 99.0)), ((-22.0, 102.0), (-6.5, 102.0)),
             ((6.5, 95.0), (24.0, 108.0))]
    for (a, b) in lines:
        L = math.dist(a, b)
        k = max(1, int(L / 2.2))
        for j in range(k):
            pa = (a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k)
            pb = (a[0] + (b[0] - a[0]) * (j + 1) / k - (b[0] - a[0]) / L * 0.08, a[1] + (b[1] - a[1]) * (j + 1) / k - (b[1] - a[1]) / L * 0.08)
            for z in (0.12, 1.05):
                bm.cyl((pa[0], pa[1], z), (pb[0], pb[1], z), 0.022, grn, n=6)
            m = 8
            for q in range(m + 1):
                x = pa[0] + (pb[0] - pa[0]) * q / m
                y = pa[1] + (pb[1] - pa[1]) * q / m
                bm.cyl((x, y, 0.12), (x, y, 1.05), 0.01, grn, n=4)
            for x, y in (pa, pb):
                bm.cyl((x, y, 0.0), (x, y, 1.1), 0.022, grn, n=6)
                bm.cyl((x - 0.25, y, 0.02), (x + 0.25, y, 0.02), 0.02, grn, n=4)
    bm.build("plaza_barriers", c)


# ---------------------------------------------------------------- 形の道具

def _sphere(mb, c, r, mat, sx=1.0, sy=1.0, sz=1.0, seg=12):
    """MB に球(楕円体)を足す。"""
    for i in range(seg // 2):
        a0, a1 = math.pi * i / (seg // 2) - math.pi / 2, math.pi * (i + 1) / (seg // 2) - math.pi / 2
        for j in range(seg):
            b0, b1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            P = lambda a, b: (c.x + r * sx * math.cos(a) * math.cos(b), c.y + r * sy * math.cos(a) * math.sin(b), c.z + r * sz * math.sin(a))
            mb.face((P(a0, b0), P(a0, b1), P(a1, b1), P(a1, b0)), mat)


def _frustum(mb, u, d, z, w0, l0, w1, l1, h, mat):
    """角錐台(台座)。下 w0×l0、上 w1×l1。"""
    B = [(u - w0 / 2, d - l0 / 2, z), (u + w0 / 2, d - l0 / 2, z), (u + w0 / 2, d + l0 / 2, z), (u - w0 / 2, d + l0 / 2, z)]
    T = [(u - w1 / 2, d - l1 / 2, z + h), (u + w1 / 2, d - l1 / 2, z + h), (u + w1 / 2, d + l1 / 2, z + h), (u - w1 / 2, d + l1 / 2, z + h)]
    for i in range(4):
        j = (i + 1) % 4
        mb.face((B[i], B[j], T[j], T[i]), mat)
    mb.face(T, mat)


def _statue(c, xf):
    """ラグビー選手の立像(高さ約 1.7 m、ブロンズ)。局所の +Y が外(広場)を向く。左足を少し前、右腕にボール。"""
    bm = bmesh.new()

    def limb(p0, p1, r0, r1, seg=12):
        p0, p1 = Vector(p0), Vector(p1)
        dv = p1 - p0
        q = dv.to_track_quat("Z", "Y")
        m = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=dv.length, matrix=m)

    def ell(cn, rx, ry, rz, rot=None):
        m = Matrix.Translation(cn) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((rx, ry, rz, 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0, matrix=m)

    for sx, fy in ((-1, 0.06), (1, -0.02)):              # 足(左足を少し前)
        x = sx * 0.1
        ell((x, fy + 0.06, 0.04), 0.055, 0.13, 0.045)
        limb((x, fy, 0.06), (x, fy, 0.46), 0.05, 0.062)                 # すね(長い靴下)
        limb((x, fy, 0.44), (x, fy, 0.48), 0.068, 0.068)                # 靴下の折り返し
        limb((x, fy, 0.47), (x * 1.05, fy * 0.5, 0.82), 0.064, 0.085)    # もも
    ell((0, 0, 0.84), 0.2, 0.13, 0.11)                                  # 短パン
    limb((0, 0, 0.82), (0, 0, 0.96), 0.19, 0.18)
    limb((0, 0, 0.95), (0, 0.01, 1.38), 0.165, 0.2)                     # 胴(ジャージ)
    ell((0, 0.01, 1.36), 0.21, 0.13, 0.07)                              # 肩
    limb((0, 0.02, 1.38), (0, 0.02, 1.43), 0.09, 0.075)                 # 襟
    limb((0, 0.02, 1.42), (0, 0.02, 1.49), 0.052, 0.05)                 # 首
    ell((0, 0.03, 1.58), 0.095, 0.105, 0.115)                           # 頭
    limb((-0.21, 0.0, 1.35), (-0.25, 0.02, 1.07), 0.052, 0.045)         # 左の上腕(下げる)
    limb((-0.25, 0.02, 1.07), (-0.24, 0.06, 0.82), 0.044, 0.036)
    ell((-0.24, 0.07, 0.79), 0.04, 0.045, 0.055)                        # 左の手
    limb((0.21, 0.0, 1.35), (0.25, -0.03, 1.08), 0.052, 0.045)          # 右の上腕
    limb((0.25, -0.03, 1.08), (0.11, 0.14, 1.06), 0.044, 0.036)         # 右の前腕(ボールを抱える)
    rot = Matrix.Rotation(math.radians(25), 4, "Y") @ Matrix.Rotation(math.radians(20), 4, "Z")
    ell((0.17, 0.12, 1.0), 0.15, 0.095, 0.095, rot)                     # ボール
    me = bpy.data.meshes.new("statue")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(M.get("bronze"))
    ob = bpy.data.objects.new("statue", me)
    ob.matrix_world = xf
    c.objects.link(ob)
