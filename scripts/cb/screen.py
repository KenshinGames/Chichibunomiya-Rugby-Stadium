"""⑥大型映像装置(得点板): 北スタンド中央の後ろ。黒い枠、左に時計、右に黒い LED の得点表示。2 本の脚で立つ。"""
import math

from . import config, materials as M
from .util import MB, coll


def build():
    S = config.load()["screen"]
    c = coll("screen")
    mb = MB()
    frame = M.get("screen_frame")
    x0 = S["x_face"]
    x1 = x0 + S["depth"]
    yc, w = S["y_center"], S["w"]
    ya, yb = yc + w / 2, yc - w / 2            # 前から見て左が +Y(西)
    zb, zt = S["z_bottom"], S["z_top"]
    mb.box(x0, x1, yb, ya, zb, zt, frame)
    # 脚
    ls = S["leg_size"] / 2
    for k in range(S["legs"]):
        y = ya - w * (k + 1) / (S["legs"] + 1)
        mb.box(x0 + 0.2, x0 + 0.2 + 2 * ls, y - ls, y + ls, 0.0, zb, M.get("grey_steel"))
    # 得点板(右側): 黒い LED の板に白い文字の行とオレンジの数字(写真 Stadium-w3、2018 年)。文字は細い四角の並びで代える
    m = 0.45
    yclock = ya - w * S["clock_frac"]
    led_bg = M.emissive("screen_image", M.srgb(20, 22, 24), 0.0, 0.0, base=M.srgb(14, 15, 16))
    led_w = M.emissive("led_white", (1.0, 1.0, 0.96, 1), 1.6, 3.0, base=M.srgb(220, 220, 215))
    led_o = M.emissive("led_orange", (1.0, 0.55, 0.15, 1), 1.6, 3.0, base=M.srgb(230, 130, 40))
    xf = x0 - 0.02
    y_l, y_r = yclock - 0.2, yb + m
    mb.face(((xf, y_l, zb + m), (xf, y_r, zb + m), (xf, y_r, zt - m), (xf, y_l, zt - m)), led_bg)
    rows = 6
    rh = (zt - zb - 2 * m) / rows
    pat = [(0.05, 0.30), (0.36, 0.55), (0.62, 0.72), (0.78, 0.95)]      # 1 行の中の文字の固まり(左からの割合)
    for k in range(rows):
        z0 = zt - m - (k + 0.72) * rh
        z1 = z0 + rh * 0.45
        mat = led_o if k == rows - 1 else led_w
        for j, (a, b) in enumerate(pat):
            if (k + j) % 5 == 4:
                continue                                                  # 空いた所も作る
            ya_, yb_ = y_l + (y_r - y_l) * a, y_l + (y_r - y_l) * b
            mb.face(((xf - 0.01, ya_, z0), (xf - 0.01, yb_, z0), (xf - 0.01, yb_, z1), (xf - 0.01, ya_, z1)), mat)
    # 時計(左側): 白い文字盤と黒い針
    cy = (ya + yclock) / 2
    cz = zb + (zt - zb) * 0.62
    r = min((ya - yclock) / 2 - 0.5, (zt - zb) * 0.28)
    face = M.emissive("clock_face", (1.0, 1.0, 1.0, 1), 0.6, 1.2, base=M.srgb(235, 235, 230))
    n = 40
    mb.face([(xf, cy - r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)], face)
    blk = M.get("black")
    for (ang, L, wd) in ((math.radians(60), r * 0.55, 0.18), (math.radians(-20), r * 0.85, 0.12)):
        dy, dz = math.cos(ang) * L, math.sin(ang) * L
        ny, nz = -math.sin(ang) * wd, math.cos(ang) * wd
        mb.face(((xf - 0.01, cy - ny, cz - nz), (xf - 0.01, cy + dy - ny, cz + dz - nz),
                 (xf - 0.01, cy + dy + ny, cz + dz + nz), (xf - 0.01, cy + ny, cz + nz)), blk)
    # 時計の下の得点表示の帯(オレンジの数字の代わり)
    mb.face(((xf, ya - m, zb + m), (xf, yclock + 0.3, zb + m), (xf, yclock + 0.3, zb + 2.2), (xf, ya - m, zb + 2.2)),
            M.emissive("score_band", M.srgb(255, 140, 40), 0.8, 1.6, base=M.srgb(40, 20, 10)))
    mb.build("screen", c)
