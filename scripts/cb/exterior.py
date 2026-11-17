"""⑦周り: 地面、運動場・公園、道路、建物、神宮球場、木。

形は config/surroundings.json(OpenStreetMap から tools/osm_surroundings.py で作ったもの)。
高さのない建物は床面積から推定してある(src = est)。スタジアムの外壁と入口はここではまだ作らない。
"""
import hashlib
import json
import math
import os
import random

from . import config, materials as M
from .util import MB, coll

WALLS = ["house_a", "house_b", "house_c", "apart_a", "apart_b", "office_a", "office_b", "office_c"]
ROAD_Z = {"trunk": 0.030, "primary": 0.028, "primary_link": 0.027, "secondary": 0.026, "secondary_link": 0.025,
          "tertiary": 0.024, "tertiary_link": 0.023, "unclassified": 0.022, "residential": 0.021,
          "living_street": 0.020, "service": 0.019, "pedestrian": 0.016, "footway": 0.014, "path": 0.013,
          "cycleway": 0.013, "steps": 0.015}
WALK = ("pedestrian", "footway", "path", "cycleway", "steps")
AREA_MAT = {"lawn": ("lawn", 0.004), "wood": ("lawn", 0.005), "court": ("court", 0.008), "pitch": ("turf2", 0.008),
            "dirt": ("dirt", 0.006), "water": ("water", 0.007)}


def load():
    with open(os.path.join(config.ROOT, "config", "surroundings.json"), encoding="utf-8") as f:
        return json.load(f)


def _h01(key):
    return int(hashlib.md5(str(key).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def build():
    S = load()
    c = coll("exterior")
    _ground(c)
    _areas(S, c)
    _roads(S, c)
    _buildings(S, c)
    if S.get("jingu"):
        _jingu(S["jingu"], c)
    _trees(S, c)


def _ground(c):
    mb = MB()
    mb.rect(-4000.0, 4000.0, -4000.0, 4000.0, -0.05, M.get("paving_grey"))
    mb.build("ground", c)


def _areas(S, c):
    mb = MB()
    for a in S["areas"]:
        name, z = AREA_MAT[a["kind"]]
        mb.face([(p[0], p[1], z) for p in a["poly"]], M.get(name))
    mb.build("areas", c)


def _roads(S, c):
    car, walk = MB(), MB()
    for r in S["roads"]:
        k, w = r["kind"], r["w"]
        z = ROAD_Z[k]
        mb = walk if k in WALK else car
        mat = M.get("paving_light") if k in WALK else M.get("asphalt")
        pts = r["line"]
        for p, q in zip(pts, pts[1:]):
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy)
            if L < 1e-3:
                continue
            nx, ny = -dy / L * w / 2, dx / L * w / 2
            mb.face(((p[0] + nx, p[1] + ny, z), (p[0] - nx, p[1] - ny, z), (q[0] - nx, q[1] - ny, z),
                     (q[0] + nx, q[1] + ny, z)), mat)
        if k not in WALK and w >= 5:
            # 曲がり角の隙間を丸い板で埋める
            for p in pts:
                n = 8
                mb.face([(p[0] + w / 2 * math.cos(2 * math.pi * i / n), p[1] + w / 2 * math.sin(2 * math.pi * i / n), z - 0.001)
                         for i in range(n)], mat)
    car.build("roads", c)
    walk.build("walks", c)


def _buildings(S, c):
    mb = MB()
    roofs = [M.get("roof_flat_a"), M.get("roof_flat_b"), M.get("concrete_dark")]
    for b in S["buildings"]:
        poly, h = b["poly"], b["h"]
        r = _h01(b["id"])
        if b["name"] == "伊藤忠商事東京本社ビル":
            wall = M.get("office_d")
        elif h > 40:
            wall = M.get(("office_a", "office_b", "office_c")[int(r * 3) % 3])
        else:
            wall = M.get(WALLS[int(r * len(WALLS)) % len(WALLS)])
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            mb.face(((p[0], p[1], 0.0), (q[0], q[1], 0.0), (q[0], q[1], h), (p[0], p[1], h)), wall)
        mb.face([(p[0], p[1], h) for p in poly], roofs[int(r * 7) % 3])
    mb.build("buildings", c)


def _ray_poly(cx, cy, ang, poly):
    """中心から角度 ang の向きの半直線が多角形と交わる一番遠い距離。"""
    dx, dy = math.cos(ang), math.sin(ang)
    best = None
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((x0 - cx) * ey - (y0 - cy) * ex) / den
        s = ((x0 - cx) * dy - (y0 - cy) * dx) / den
        if t > 0 and 0 <= s <= 1:
            best = t if best is None else max(best, t)
    return best


def _jingu(J, c):
    """明治神宮野球場: 外形と競技場の外形のあいだを、角度ごとに斜めの客席でつなぐ(大きな形だけ)。"""
    outer, inner = J["outer"], J["inner"]
    cx = sum(p[0] for p in inner) / len(inner)
    cy = sum(p[1] for p in inner) / len(inner)
    mb = MB()
    seats, wall, field = M.get("jingu_seats"), M.get("brick_wall"), M.get("turf2")
    n = 120
    ring = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ro = _ray_poly(cx, cy, a, outer)
        ri = _ray_poly(cx, cy, a, inner)
        if ro is None or ri is None:
            continue
        ri = min(ri, ro - 8.0)
        ring.append((a, ri, ro))
    z_in, z_out = 3.0, 19.0
    for k in range(len(ring)):
        a0, ri0, ro0 = ring[k]
        a1, ri1, ro1 = ring[(k + 1) % len(ring)]
        P = lambda a, r, z: (cx + r * math.cos(a), cy + r * math.sin(a), z)
        mb.face((P(a0, ri0, z_in), P(a1, ri1, z_in), P(a1, ro1, z_out), P(a0, ro0, z_out)), seats)
        mb.face((P(a1, ro1, 0.0), P(a0, ro0, 0.0), P(a0, ro0, z_out), P(a1, ro1, z_out)), wall)
        mb.face((P(a0, ri0, 0.0), P(a1, ri1, 0.0), P(a1, ri1, z_in), P(a0, ri0, z_in)), M.get("concrete"))
    mb.face([(cx + r * math.cos(a), cy + r * math.sin(a), 0.02) for (a, r, _) in ring], field)
    mb.build("jingu_stadium", c)


def _blob(mb, cx, cy, cz, rx, rz, mat, seg=7, rings=4):
    pts = []
    for j in range(rings + 1):
        ph = math.pi * j / rings
        for i in range(seg):
            th = 2 * math.pi * i / seg
            pts.append((cx + rx * math.sin(ph) * math.cos(th), cy + rx * math.sin(ph) * math.sin(th), cz + rz * math.cos(ph)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            mb.face((pts[a + seg], pts[b + seg], pts[b], pts[a]), mat)


def _inside(pt, poly):
    x, y = pt
    cin = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            cin = not cin
    return cin


def tree_points(S):
    """木の位置: OSM の木、並木(8 m ごと)、林と公園の中(面積に応じて乱数で)、大きな道の両側(12 m ごと)。"""
    rnd = random.Random(1947)
    pts = [tuple(p) for p in S["trees"]]
    for row in S["tree_rows"]:
        for p, q in zip(row, row[1:]):
            L = math.dist(p, q)
            k = max(1, int(L / 8.0))
            pts += [(p[0] + (q[0] - p[0]) * i / k, p[1] + (q[1] - p[1]) * i / k) for i in range(k)]
    for a in S["areas"]:
        if a["kind"] not in ("wood", "lawn"):
            continue
        poly = a["poly"]
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        A = abs(0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                          for i in range(len(poly))))
        dens = 70.0 if a["kind"] == "wood" else 260.0
        for _ in range(min(400, int(A / dens))):
            p = (rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys)))
            if _inside(p, poly):
                pts.append(p)
    for r in S["roads"]:
        if r["kind"] not in ("trunk", "primary", "secondary"):
            continue
        off = r["w"] / 2 - 1.2
        for p, q in zip(r["line"], r["line"][1:]):
            L = math.dist(p, q)
            if L < 1:
                continue
            nx, ny = -(q[1] - p[1]) / L, (q[0] - p[0]) / L
            for i in range(int(L / 12.0)):
                t = (i + 0.5) * 12.0 / L
                x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
                pts += [(x + nx * off, y + ny * off), (x - nx * off, y - ny * off)]
    # 建物の中に入った木は捨てる(大きな建物だけ調べる)
    big = [b["poly"] for b in S["buildings"] if b["h"] > 12]
    boxes = [(min(p[0] for p in q), max(p[0] for p in q), min(p[1] for p in q), max(p[1] for p in q)) for q in big]
    out = []
    for p in pts:
        if math.hypot(p[0], p[1]) > 650:
            continue
        hit = False
        for q, (x0, x1, y0, y1) in zip(big, boxes):
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and _inside(p, q):
                hit = True
                break
        if not hit:
            out.append(p)
    return out


def _trees(S, c):
    rnd = random.Random(1953)
    mb = MB()
    trunk = M.get("trunk")
    leaves = [M.get("leaf_a"), M.get("leaf_b")]
    pts = tree_points(S)
    for (x, y) in pts:
        h = rnd.uniform(7.0, 14.0)
        r = h * rnd.uniform(0.25, 0.36)
        mb.cyl((x, y, 0), (x, y, h * 0.55), 0.22, trunk, n=5)
        lf = leaves[rnd.randrange(2)]
        _blob(mb, x, y, h * 0.7, r, h * 0.34, lf)
        _blob(mb, x + r * 0.4, y - r * 0.3, h * 0.58, r * 0.7, h * 0.24, lf)
    print("[exterior] 木 %d 本" % len(pts))
    mb.build("trees", c, smooth=True)
