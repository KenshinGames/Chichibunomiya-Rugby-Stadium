"""⑥大型映像装置: 北スタンド中央の後ろ。黒い枠、左に時計、右に映像。2 本の脚で立つ。"""
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
    # 映像(右側)。昼も少し光る
    m = 0.45
    yclock = ya - w * S["clock_frac"]
    scr = M.emissive("screen_image", M.srgb(70, 150, 90), 1.4, 1.8, base=M.srgb(30, 70, 40))
    xf = x0 - 0.02
    mb.face(((xf, yclock - 0.2, zb + m), (xf, yb + m, zb + m), (xf, yb + m, zt - m), (xf, yclock - 0.2, zt - m)), scr)
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
