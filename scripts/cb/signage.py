"""⑥看板: 四方のスタンドの前の壁に並ぶ横長の広告。社名はすべて架空(実在の企業名・ロゴは使わない)。

写真 03・05(前の壁に白い看板がほぼ切れ目なく並び、ところどころ赤・紺)、04・01(北とメインの前に赤い看板)。
1 枚の幅 6 m、高さは前の壁に収まる 1 m 前後(推定)。ゲート番号の数字はまだ(出入口の白い札だけ)。
"""
from mathutils import Vector

from . import layout, materials as M
from .util import MB, coll, text_obj

# 架空の社名(ラグビーの用語と外苑・青山の言葉から作った。実在の企業とは関係ない)。(名前, 日本語か, 地の色, 字の色)
NAMES = [
    ("TRYLINE SPORTS", False, "sign_white", "sign_navy"),
    ("ガイエン食品", True, "sign_white", "sign_red"),
    ("RUCK ENERGY", False, "sign_red", "text_white"),
    ("イチョウ生命", True, "sign_white", "sign_green"),
    ("LINEOUT COFFEE", False, "sign_white", "text_dark"),
    ("キタアオヤマ電機", True, "sign_navy", "text_white"),
    ("MAUL & CO.", False, "sign_white", "sign_blue"),
    ("コノハ運輸", True, "sign_white", "sign_red"),
    ("TOUCHLINE BANK", False, "sign_blue", "text_white"),
    ("ゴールポスト建設", True, "sign_white", "text_dark"),
    ("DROP GOAL WATER", False, "sign_white", "sign_blue"),
    ("ハーフウェイ証券", True, "sign_red", "text_white"),
]

BOARD_L = 6.0          # 1 枚の幅(推定)


def _board(mb, c, xf, nrm, u0, u1, z0, z1, idx, tag):
    name, jp, bg, fg = NAMES[idx % len(NAMES)]
    mb.box(u0, u1, -0.11, -0.01, z0, z1, M.get(bg))
    p = xf @ Vector(((u0 + u1) / 2, -0.13, (z0 + z1) / 2))
    text_obj("ad_" + tag, name, (z1 - z0) * (0.5 if jp else 0.42), M.get(fg), c, p, nrm, jp=jp,
             max_width=(u1 - u0) * 0.86)


def build():
    c = coll("signage")
    for k, name in enumerate(("west", "east", "north", "south")):
        st = layout.stand(name)
        xf = layout.xf(name)
        nrm = (xf.to_3x3() @ Vector((0, -1, 0))).normalized()
        fh = st["front_wall_h"]
        z1 = fh - 0.08
        z0 = max(0.08, z1 - 1.0)
        a, b = layout.u_range(st, 0.0)
        a, b = a + 1.0, b - 1.0
        n = int((b - a) // BOARD_L)
        off = a + ((b - a) - n * BOARD_L) / 2
        mb = MB(xf)
        for i in range(n):
            u0 = off + i * BOARD_L + 0.06
            u1 = off + (i + 1) * BOARD_L - 0.06
            _board(mb, c, xf, nrm, u0, u1, z0, z1, i * 5 + k * 3, "%s%02d" % (name, i))
        mb.build("signs_wall_" + name, c)
    print("[signage] 前の壁の看板(社名は架空)")
