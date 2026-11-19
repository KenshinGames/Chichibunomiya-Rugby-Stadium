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

WALLS = ["house_a", "house_b", "house_c", "apart_a", "apart_b", "apart_c", "office_a", "office_b", "office_c",
         "office_e", "office_f"]
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
    _main_gate(c)
    _jingu_towers(c)
    for st in S.get("stadiums", []):
        if S.get("jingu") and _near(st["outer"], S["jingu"]["outer"]):
            continue                      # 神宮球場は _jingu で作る
        _bowl(st, c)
    _trees(S, c)


def _main_gate(c):
    """正面入場口の門と、メインの裏の中央の細部(entrance.py)、広場と夜の光。"""
    from . import entrance, stands
    entrance.gate(c)
    entrance.facade_center(c, stands.FACADE)
    _main_plaza(c)
    _plaza_night(c)


PLAZA = dict(x0=-66.0, x1=70.0, y0=78.0, y1=127.5, keep=7.5, stall_w=2.5, stall_l=5.0,
             near_row=78.6, lanes=(87.0, 112.0), lane_gap=2.5, block=(9.0, 64.0))
# メインの裏の広場。写真 84327(2025-01-19、正面から)・413(2019)・724(2025):
#   暗いアスファルト。外壁ぎわは車を外壁へ向けて止める区画(写真 413)、その先の広い所は外壁と平行な長い線が 2.5 m おき(写真 84327)、
#   線の端をそろえる直角の線。中央の大階段と門からの通り(|X| < 7.5)には線がない。線の数と長さは写真からの読み取り(±1 本)


def _main_plaza(c):
    P = PLAZA
    mb = MB()
    asph = M.get("asphalt_dark")
    line = M.get("white_paint")
    mb.rect(P["x0"], P["x1"], P["y0"], P["y1"], 0.0175, asph)      # 歩道(0.014〜0.016)より上、車道より下
    z = 0.018
    y = P["near_row"]
    for sx in (-1, 1):
        xa, xb = (P["keep"], P["x1"] - 1.0) if sx > 0 else (P["x0"] + 1.0, -P["keep"])
        n = int((xb - xa) / P["stall_w"])
        for k in range(n + 1):
            x = xa + P["stall_w"] * k
            mb.rect(x - 0.06, x + 0.06, y, y + P["stall_l"], z, line)
        mb.rect(xa, xa + n * P["stall_w"], y + P["stall_l"] - 0.06, y + P["stall_l"] + 0.06, z, line)
    ya, yb = P["lanes"]
    bx0, bx1 = P["block"]
    for sx in (-1, 1):
        xa, xb = sorted((sx * bx0, sx * bx1))
        k = int((yb - ya) / P["lane_gap"])
        for j in range(k + 1):
            yy = ya + P["lane_gap"] * j
            mb.rect(xa, xb, yy - 0.06, yy + 0.06, z, line)
        xe = sx * bx0
        mb.rect(xe - 0.06, xe + 0.06, ya, ya + P["lane_gap"] * k, z, line)
    mb.build("main_plaza", c)


def _plaza_night(c):
    """正面入場口の夜: 外壁と広場を照らす面の光(街灯は entrance.py の球の街灯と曲がった街灯)。"""
    from mathutils import Vector
    from .lights import _area
    nc = coll("night_lights")
    for (x, energy) in ((-30.0, 1.6e4), (0.0, 2.0e4), (30.0, 1.6e4)):
        _area("facade_light_%d" % int(x), nc, Vector((x, 112.0, 9.0)), (0.0, -1.0, -0.25), 26.0, 6.0, energy, spread=110.0)
    _area("plaza_light", nc, Vector((1.0, 112.0, 12.0)), (0.0, 0.0, -1.0), 30.0, 30.0, 1.2e4, spread=120.0)


# 神宮球場の照明塔(白い 2 本柱、大きな灯具)。比較 04 と 01 の解いたカメラからの向きの交点 [X, Y, 灯具の中心の高さ]。
# 2 枚の写真の灯具の高さはほぼ一致(4 基目は写真の端で ±3 m)。神宮球場の中心から 112〜118 m の輪の上。残りの塔は写真にない
JINGU_TOWERS = [(236.0, 131.0, 38.0), (143.0, 44.0, 36.5), (145.0, -18.0, 35.0), (163.0, -53.0, 26.5)]
JINGU_CENTER = (253.0, 14.0)


def _jingu_towers(c):
    """神宮球場の照明塔。灯具は幅 16 m・高さ 6 m(写真 04 の見かけの幅から)、球場の中心へ向ける。夜は光る。"""
    from mathutils import Matrix, Vector
    from .lights import _lens
    white, lens = M.get("white_paint"), _lens()
    for i, (x, y, zc) in enumerate(JINGU_TOWERS):
        a = math.atan2(JINGU_CENTER[1] - y, JINGU_CENTER[0] - x)
        xf = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(a - math.pi / 2, 4, "Z")   # 局所 +Y が球場の中心へ
        mb = MB(xf)
        for px in (-4.5, 4.5):
            mb.cyl((px, 0, 0), (px, 0, zc - 3.0), 0.55, white, n=10)
            mb.cyl((px, 0, zc - 3.5), (px * 0.6, 1.2, zc - 2.0), 0.3, white, n=8)
        mb.box(-8.0, 8.0, 0.8, 1.6, zc - 3.0, zc + 3.0, white)            # 灯具の枠
        mb.box(-7.6, 7.6, 1.6, 1.7, zc - 2.7, zc + 2.7, lens)             # 灯具の面(球場の側)
        mb.build("jingu_tower_%d" % i, c)


def _near(a, b, tol=40.0):
    ca = (sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a))
    cb = (sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b))
    return math.dist(ca, cb) < tol


def _bowl(st, c):
    """屋根のある競技場(国立競技場、OSM の名前は MUFGスタジアム)の大きな形。
    内周から外へ上がる客席、木の軒の色の外壁、客席を覆う屋根の輪(内側の縁は内周の 6 m 外)、トラックと芝。
    高さは OSM(50.5 m)。客席の上端の高さ、屋根の傾きは推定。"""
    outer, inner = st["outer"], st["inner"]
    cx = sum(p[0] for p in inner) / len(inner)
    cy = sum(p[1] for p in inner) / len(inner)
    H = st["h"]
    mb = MB()
    seats, wall, roof, conc = M.get("nat_seats"), M.get("wood_louver"), M.get("roof_sheet"), M.get("concrete")
    n = 144
    ring = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ro = _ray_poly(cx, cy, a, outer)
        ri = _ray_poly(cx, cy, a, inner)
        if ro is None or ri is None:
            continue
        ri = min(ri, ro - 20.0)
        ring.append((a, ri, ro))
    P = lambda a, r, z: (cx + r * math.cos(a), cy + r * math.sin(a), z)
    z_in, z_top = 1.5, H - 12.0           # 客席は内周 1.5 m から外周の手前で H-12 m まで
    z_eave, z_roof_in = H - 4.0, H - 8.0   # 屋根: 外周で H-4 m、内側の縁で H-8 m
    for k in range(len(ring)):
        a0, ri0, ro0 = ring[k]
        a1, ri1, ro1 = ring[(k + 1) % len(ring)]
        rs0, rs1 = ro0 - 6.0, ro1 - 6.0           # 客席の上端(外周の 6 m 内)
        rr0, rr1 = ri0 + 6.0, ri1 + 6.0           # 屋根の内側の縁
        mb.face((P(a0, ri0, z_in), P(a1, ri1, z_in), P(a1, rs1, z_top), P(a0, rs0, z_top)), seats)
        mb.face((P(a0, rs0, z_top), P(a1, rs1, z_top), P(a1, ro1, z_top), P(a0, ro0, z_top)), conc)
        mb.face((P(a0, ri0, 0.0), P(a1, ri1, 0.0), P(a1, ri1, z_in), P(a0, ri0, z_in)), conc)
        # 外壁: 3 段の軒(外へ少しずつ張り出す)
        for (z0, z1, dr) in ((0.0, H * 0.33, 0.0), (H * 0.33, H * 0.66, 2.0), (H * 0.66, z_eave, 4.0)):
            mb.face((P(a1, ro1 + dr, z0), P(a0, ro0 + dr, z0), P(a0, ro0 + dr, z1), P(a1, ro1 + dr, z1)), wall)
            mb.face((P(a0, ro0, z1), P(a1, ro1, z1), P(a1, ro1 + dr + 2.0, z1), P(a0, ro0 + dr + 2.0, z1)), wall)
        # 屋根: 上面と下面
        mb.face((P(a0, rr0, z_roof_in), P(a1, rr1, z_roof_in), P(a1, ro1 + 6.0, z_eave), P(a0, ro0 + 6.0, z_eave)), roof)
        mb.face((P(a1, rr1, z_roof_in - 0.6), P(a0, rr0, z_roof_in - 0.6), P(a0, ro0 + 6.0, z_eave - 0.6), P(a1, ro1 + 6.0, z_eave - 0.6)), wall)
        mb.face((P(a1, rr1, z_roof_in - 0.6), P(a1, rr1, z_roof_in), P(a0, rr0, z_roof_in), P(a0, rr0, z_roof_in - 0.6)), roof)
    mb.face([P(a, r, 0.03) for (a, r, _) in ring], M.get("track_red"))
    mb.face([P(a, r * 0.78, 0.05) for (a, r, _) in ring], M.get("turf2"))
    mb.build("stadium_%s" % st["id"], c)
    print("[exterior] 競技場 %s(高さ %.1f m)" % (st["name"] or st["id"], H))


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


def _poly_area_c(poly):
    A = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        k = x0 * y1 - x1 * y0
        A += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    if abs(A) < 1e-6:
        return 0.0, poly[0]
    return abs(A) / 2, (cx / (3 * A), cy / (3 * A))


def _roof_box(mb, poly, cx, cy, sx, sy, z0, z1, mat):
    """屋上の箱。四隅が屋根の中に入るときだけ置く。"""
    corners = [(cx - sx, cy - sy), (cx + sx, cy - sy), (cx + sx, cy + sy), (cx - sx, cy + sy)]
    if all(_inside(p, poly) for p in corners):
        mb.box(cx - sx, cx + sx, cy - sy, cy + sy, z0, z1, mat)
        return True
    return False


# かまぼこ形の白い屋根の建物(写真 03 のバックスタンドの右奥。外苑の室内球技場とバッティングドーム)
VAULTS = ("室内球技場", "バッティングドーム")


def _vault(mb, poly, h, wall, roof):
    """外形をいちばん長い辺の向きの長方形とみなし、壁を h の 45% まで立ててその上をかまぼこ形の屋根で覆う。"""
    n = len(poly)
    i = max(range(n), key=lambda i: math.dist(poly[i], poly[(i + 1) % n]))
    p, q = poly[i], poly[(i + 1) % n]
    L = math.dist(p, q)
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    vx, vy = -uy, ux
    us = [(a[0] - p[0]) * ux + (a[1] - p[1]) * uy for a in poly]
    vs = [(a[0] - p[0]) * vx + (a[1] - p[1]) * vy for a in poly]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    P = lambda u, v, z: (p[0] + ux * u + vx * v, p[1] + uy * u + vy * v, z)
    zw = h * 0.45
    for (a, b) in (((u0, v0), (u1, v0)), ((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))):
        mb.face((P(a[0], a[1], 0), P(b[0], b[1], 0), P(b[0], b[1], zw), P(a[0], a[1], zw)), wall)
    k = 16
    W = v1 - v0
    arc = [(v0 + W * j / k, zw + (h - zw) * math.sin(math.pi * j / k)) for j in range(k + 1)]
    for j in range(k):
        (va, za), (vb, zb) = arc[j], arc[j + 1]
        mb.face((P(u0, va, za), P(u0, vb, zb), P(u1, vb, zb), P(u1, va, za)), roof)
    for uu in (u0, u1):
        mb.face([P(uu, v, z) for v, z in arc], wall)


def _buildings(S, c):
    """建物: 外形を高さまで立ち上げる。屋上の縁(パラペット)を 0.9 m 立ち上げ、
    大きな屋根には設備の箱や塔屋を載せる(形は推定。遠目の輪郭を単調にしないため)。"""
    mb = MB()
    roofs = [M.get("roof_flat_a"), M.get("roof_flat_b"), M.get("concrete_dark")]
    gear = M.get("roof_gear")
    for b in S["buildings"]:
        poly, h = b["poly"], b["h"]
        r = _h01(b["id"])
        rnd = random.Random(b["id"])
        if b["name"] == "伊藤忠商事東京本社ビル":
            wall = M.get("office_d")
        elif h >= 60:
            # 高さ 60 m 以上の塔はガラスの外壁(青山の高層は 1990 年代以降のガラス張りが多い。写真 05・02)
            wall = M.get(("office_glass", "office_glass2")[int(r * 2) % 2])
        elif h > 40:
            wall = M.get(("office_a", "office_b", "office_c", "office_e", "office_f")[int(r * 5) % 5])
        elif h > 14:
            wall = M.get(("apart_a", "apart_b", "apart_c", "office_a", "office_b", "office_c", "office_e",
                          "office_f")[int(r * 8) % 8])
        else:
            wall = M.get(WALLS[int(r * len(WALLS)) % len(WALLS)])
        if b["name"] in VAULTS:
            _vault(mb, poly, h, M.get("factory_wall"), M.get("roof_membrane"))
            continue
        area, (cx, cy) = _poly_area_c(poly)
        par = 0.9 if h > 7 and area > 60 else 0.0
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            mb.face(((p[0], p[1], 0.0), (q[0], q[1], 0.0), (q[0], q[1], h + par), (p[0], p[1], h + par)), wall)
        mb.face([(p[0], p[1], h) for p in poly], roofs[int(r * 7) % 3])
        if area < 120 or h < 8 or not _inside((cx, cy), poly):
            continue
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        ext = min(max(xs) - min(xs), max(ys) - min(ys))
        if h > 24 and rnd.random() < 0.7:
            # 塔屋(階段室・機械室): 壁と同じ材料
            s = ext * rnd.uniform(0.12, 0.2)
            _roof_box(mb, poly, cx, cy, s * rnd.uniform(0.8, 1.4), s, h, h + rnd.uniform(3.0, 4.5), wall)
        for _ in range(rnd.randint(1, 4) if area > 300 else rnd.randint(0, 2)):
            s = max(0.8, ext * rnd.uniform(0.04, 0.09))
            ox = cx + rnd.uniform(-0.3, 0.3) * (max(xs) - min(xs))
            oy = cy + rnd.uniform(-0.3, 0.3) * (max(ys) - min(ys))
            _roof_box(mb, poly, ox, oy, s * rnd.uniform(0.7, 1.6), s, h, h + rnd.uniform(1.0, 2.2), gear)
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
    """木の位置と大きさの種類 [(x, y, kind)]: OSM の木、並木(8 m ごと)、林と公園の中(面積に応じて乱数で)、
    大きな道の両側(12 m ごと)、空中写真の濃い緑(trees_aerial)。kind で高さを変える(TREE_H)。"""
    rnd = random.Random(1947)
    pts = [(p[0], p[1], "osm") for p in S["trees"]]
    pts += [(p[0], p[1], "aerial") for p in S.get("trees_aerial", [])]
    for row in S["tree_rows"]:
        for p, q in zip(row, row[1:]):
            L = math.dist(p, q)
            k = max(1, int(L / 8.0))
            pts += [(p[0] + (q[0] - p[0]) * i / k, p[1] + (q[1] - p[1]) * i / k, "row") for i in range(k)]
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
                pts.append((p[0], p[1], a["kind"]))
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
                pts += [(x + nx * off, y + ny * off, "road"), (x - nx * off, y - ny * off, "road")]
    # 建物の中に入った木は捨てる(大きな建物だけ調べる)
    big = [b["poly"] for b in S["buildings"] if b["h"] > 12]
    boxes = [(min(p[0] for p in q), max(p[0] for p in q), min(p[1] for p in q), max(p[1] for p in q)) for q in big]
    out = []
    for p in pts:
        if math.hypot(p[0], p[1]) > 650:
            continue
        hit = False
        for q, (x0, x1, y0, y1) in zip(big, boxes):
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and _inside(p[:2], q):
                hit = True
                break
        if not hit:
            out.append(p)
    return out


# 木の高さ(m)の幅。神宮外苑の林・並木(イチョウ、ケヤキ、写真 03 の左の針葉樹)は 15〜22 m、街路樹は低め(推定)
TREE_H = {"wood": (13.0, 21.0), "row": (14.0, 20.0), "aerial": (12.0, 20.0), "lawn": (9.0, 16.0),
          "osm": (9.0, 16.0), "road": (7.0, 12.0)}


# 門の内側、道から見て左(+X)の柵ぎわの背の高い針葉樹(写真 724・70564・202304011520)。OSM にも空中写真の木にもないので足す。位置は写真からの読み取り
GATE_CONIFERS = [(9.5, 128.6), (14.5, 128.3), (20.0, 128.8)]   # 柵のすぐ内側(写真 724・70564 で開口の外に見える)


def _trees(S, c):
    from . import trees
    from .util import coll as _coll
    rnd = random.Random(1953)
    pts = tree_points(S) + [(x, y, "wood") for (x, y) in GATE_CONIFERS]
    hs = [rnd.uniform(*TREE_H.get(kind, (7.0, 14.0))) for (_, _, kind) in pts]
    trees.build_trees(pts, hs, _coll("trees", c))
