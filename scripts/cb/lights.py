"""⑥照明塔 4 基と、夜に光らせる面の光。花園の lights.py の照明塔の部分を秩父宮の寸法で使う。"""
import math

import bpy
from mathutils import Vector

from . import config, materials as M
from .util import MB, coll, frame_xf

LAMP_COLOR = (1.0, 0.96, 0.90, 1.0)


def _lens():
    return M.emissive("lamp_lens", LAMP_COLOR, 0.0, 90.0, base=(0.75, 0.76, 0.74, 1.0))


def _area(name, c, loc, direction, w, h, energy, spread=120.0):
    li = bpy.data.lights.new(name, "AREA")
    li.shape = "RECTANGLE"
    li.size = w
    li.size_y = h
    li.energy = energy
    li.color = LAMP_COLOR[:3]
    li.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False
    c.objects.link(ob)
    return ob


def build():
    cfg = config.load()
    c = coll("lights")
    nc = coll("night_lights")
    T = cfg["towers"]
    pole = M.get("tower_pole")
    dark = M.get("dark_steel")
    lens = _lens()
    bw, bh = T["bank_w"], T["bank_h"]
    tilt = math.radians(T["tilt_deg"])
    for tag, (x, y, H) in T["positions"].items():
        mb = MB()
        zc = H - bh / 2
        mb.cyl((x, y, 0), (x, y, zc + 0.8), T["pole_r_bottom"], pole, n=24, r1=T["pole_r_top"], caps=True)
        # 枠はフィールドの中心を向き、少し下へ傾く
        horiz = Vector((-x, -y, 0)).normalized()
        centre = Vector((x, y, zc)) + horiz * 1.2
        n = (horiz * math.cos(tilt) + Vector((0, 0, -1)) * math.sin(tilt)).normalized()
        mb.xf = frame_xf(centre, n)
        rows, cols = T["rows"], T["cols"]
        for yy in (-bh / 2, bh / 2):
            mb.bar((-bw / 2, yy, -0.25), (bw / 2, yy, -0.25), 0.14, 0.14, dark)
        for i in range(7):
            xx = -bw / 2 + bw * i / 6
            mb.bar((xx, -bh / 2, -0.25), (xx, bh / 2, -0.25), 0.12, 0.12, dark)
        for r in range(rows):
            yy = -bh / 2 + bh * (r + 0.5) / rows
            mb.bar((-bw / 2, yy - 0.42, -0.2), (bw / 2, yy - 0.42, -0.2), 0.08, 0.08, dark)
            mb.box(-bw / 2, bw / 2, yy - 0.62, yy - 0.56, -1.0, -0.3, dark)
            for k in range(cols):
                xx = -bw / 2 + bw * (k + 0.5) / cols
                mb.box(xx - 0.36, xx + 0.36, yy - 0.30, yy + 0.30, -0.15, 0.32, dark)
                mb.face(((xx - 0.31, yy - 0.25, 0.325), (xx + 0.31, yy - 0.25, 0.325),
                         (xx + 0.31, yy + 0.25, 0.325), (xx - 0.31, yy + 0.25, 0.325)), lens)
        for xx in (-bw * 0.3, 0.0, bw * 0.3):
            mb.bar((0, -0.5, -1.2), (xx, 0, -0.25), 0.16, 0.16, dark)
        for xx in (-bw * 0.36, bw * 0.36):
            mb.cyl((xx, bh / 2, -0.25), (xx, bh / 2 + 2.6, -0.25), 0.03, dark, n=5)
        mb.build("tower_" + tag, c)
        loc = centre + n * 1.0
        _area("tower_light_" + tag, nc, loc, (Vector((x * 0.2, y * 0.2, 0.0)) - loc), bw, bh, 6.0e4, spread=100.0)
