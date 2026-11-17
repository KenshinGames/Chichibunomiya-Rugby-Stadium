"""OpenStreetMap の建物・道路・運動場・木を、模型の座標(m)に直して config/surroundings.json に書く。

  python3 tools/osm_surroundings.py

読むもの: refs/osm/buildings.json、highways.json、areas.json(Overpass API で取ったもの。取り方は docs/plan.md)
書くもの: config/surroundings.json(build はこれだけを読む。refs/ は git に入らないため)
出どころ: © OpenStreetMap contributors(ODbL)。高さのない建物は床面積から推定する(下の est_height)。
"""
import hashlib
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config", "dimensions.json")))
LAT0 = CFG["site"]["latitude"]
LON0 = CFG["site"]["longitude"]
AZ = math.radians(CFG["site"]["x_axis_azimuth_deg"])
UX = (math.sin(AZ), math.cos(AZ))      # +X の向き(東, 北)
UY = (-UX[1], UX[0])                   # +Y は +X の左

# 高さが OSM にない目立つ建物(推定。docs/reference.md)
MANUAL_H = {
    "伊藤忠商事東京本社ビル": 95.0,      # 写真 040 の窓の段数(約 22 階)から
    "青山OM-SQUARE": 100.0,            # OSM の 24 階 × 約 4.2 m
}

ROAD_W = {"trunk": 30.0, "primary": 20.0, "primary_link": 8.0, "secondary": 14.0, "secondary_link": 7.0,
          "tertiary": 10.0, "tertiary_link": 6.0, "unclassified": 7.0, "residential": 6.0, "living_street": 5.0,
          "service": 4.5, "pedestrian": 6.0, "footway": 2.5, "path": 2.0, "cycleway": 2.0, "steps": 2.5}


def xy(p):
    e = (p["lon"] - LON0) * math.cos(math.radians(LAT0)) * 111320.0
    n = (p["lat"] - LAT0) * 110574.0
    return (round(e * UX[0] + n * UX[1], 2), round(e * UY[0] + n * UY[1], 2))


def area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def join_ways(geoms):
    """relation の同じ役割の way(点列)を端でつないで、閉じた輪の一覧にする。"""
    segs = [[xy(p) for p in g] for g in geoms if g]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while math.dist(cur[0], cur[-1]) > 0.05 and changed:
            changed = False
            for i, sg in enumerate(segs):
                if math.dist(cur[-1], sg[0]) < 0.05:
                    cur += sg[1:]; segs.pop(i); changed = True; break
                if math.dist(cur[-1], sg[-1]) < 0.05:
                    cur += list(reversed(sg))[1:]; segs.pop(i); changed = True; break
        pts = cur[:-1] if math.dist(cur[0], cur[-1]) < 0.05 else cur
        out = []
        for p in pts:
            if not out or math.dist(out[-1], p) > 0.05:
                out.append(p)
        if len(out) >= 3:
            if area(out) < 0:
                out.reverse()
            rings.append(out)
    return rings


LOW_KINDS = ("parking", "garage", "garages", "sports_hall", "sports_centre", "warehouse", "grandstand")


def height_of(e_id, t, name, a):
    if name in MANUAL_H:
        return MANUAL_H[name], "manual"
    if parse_num(t.get("height")):
        return parse_num(t.get("height")), "height"
    if parse_num(t.get("building:levels")):
        return levels_height(parse_num(t.get("building:levels"))), "levels"
    if t.get("sport") or t.get("building") in LOW_KINDS:
        # 屋内のテニス場・駐車場など: 床面積が大きくても低い(写真 03 のバックスタンドの後ろのかまぼこ屋根)
        return 9.0 + 4.0 * rnd01(e_id), "est"
    return est_height(e_id, a), "est"


def ring(geom):
    """way の geometry を閉じた点列(最後の重複を除く、反時計回り)にする。"""
    pts = [xy(p) for p in geom]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 0.05:
            out.append(p)
    if len(out) >= 3 and area(out) < 0:
        out.reverse()
    return out


def stadium_zone():
    """スタンドと芝の範囲(この中の OSM の建物・道は作らない)。外へ 2 m 広げた箱の集まり。"""
    zs = [(-75.0, 73.0, -43.0, 43.0)]                       # 芝と前の通路
    zs += [(-71.0, 73.0, 40.0, 78.0), (-90.0, 89.0, -78.0, -40.0),   # 西、東
           (69.0, 91.0, -37.0, 35.0), (-96.0, -72.0, -39.0, 39.0)]   # 北、南
    return zs


def in_zone(pt):
    return any(x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1 for (x0, x1, y0, y1) in stadium_zone())


def rnd01(key, salt=""):
    h = hashlib.md5(("%s%s" % (key, salt)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def est_height(wid, a):
    """床面積 a(m²)から高さを推定(北青山の町並み: 小さな家は 2 階、通り沿いは中層)。"""
    r = rnd01(wid)
    if a < 80:
        return 6.0 + 2.0 * r
    if a < 200:
        return 7.0 + 6.0 * r
    if a < 600:
        return 10.0 + 14.0 * r
    if a < 2000:
        return 14.0 + 20.0 * r
    return 18.0 + 22.0 * r


def levels_height(lv):
    per = 3.0 if lv <= 5 else (3.6 if lv <= 12 else 4.1)
    return lv * per + 1.0


def parse_num(s):
    try:
        return float(str(s).replace("m", "").replace(" ", "").split(";")[0])
    except ValueError:
        return None


def main():
    load = lambda n: json.load(open(os.path.join(ROOT, "refs", "osm", n + ".json")))["elements"]
    out = {"_comment": "OpenStreetMap から作った周りの建物・道路・運動場・木。座標は模型の X, Y(m)。"
                       "高さ h の出どころは src(height=OSM の高さ、levels=OSM の階数から、manual=手で決めた推定、est=床面積から推定)。"
                       "© OpenStreetMap contributors(ODbL)。作り直し: python3 tools/osm_surroundings.py",
           "buildings": [], "roads": [], "areas": [], "trees": [], "tree_rows": [], "jingu": None, "stadiums": []}
    skipped = 0
    for e in load("buildings"):
        if e["type"] != "way" or "geometry" not in e:
            continue
        t = e.get("tags", {})
        poly = ring(e["geometry"])
        if len(poly) < 3:
            continue
        a = area(poly)
        c = centroid(poly)
        if in_zone(c) or t.get("building") in ("roof",) and in_zone(c):
            skipped += 1
            continue
        name = t.get("name", "")
        h, src = height_of(e["id"], t, name, a)
        if t.get("building") == "roof":
            h = min(h, 6.0)
        out["buildings"].append({"id": e["id"], "name": name, "kind": t.get("building", "yes"), "h": round(h, 1),
                                 "src": src, "poly": poly})
    # relation の建物(multipolygon)。内周のある競技場は stadiums へ、ほかは外周を建物として足す
    for e in load("buildings"):
        if e["type"] != "relation":
            continue
        t = e.get("tags", {})
        if t.get("type") != "multipolygon":
            continue                       # type=building(outline と part)は way の側に入っている
        name = t.get("name", "")
        mem = e.get("members", [])
        outers = join_ways([m.get("geometry") for m in mem if m.get("role") == "outer"])
        inners = join_ways([m.get("geometry") for m in mem if m.get("role") == "inner"])
        if not outers:
            continue
        c = centroid(outers[0])
        if in_zone(c):
            skipped += 1
            continue
        h, src = height_of(e["id"], t, name, area(outers[0]))
        if t.get("building") == "stadium" and inners:
            out["stadiums"].append({"id": e["id"], "name": name, "h": round(h, 1), "src": src,
                                    "outer": outers[0], "inner": inners[0]})
            continue
        for k, o in enumerate(outers):
            out["buildings"].append({"id": e["id"] * 10 + k, "name": name, "kind": t.get("building", "yes"),
                                     "h": round(h, 1), "src": src, "poly": o})
    for e in load("highways"):
        t = e.get("tags", {})
        k = t.get("highway")
        if k not in ROAD_W or "geometry" not in e:
            continue
        if t.get("layer", "0").startswith("-") or t.get("tunnel") == "yes":
            continue
        line = [xy(p) for p in e["geometry"]]
        w = parse_num(t.get("width")) or ROAD_W[k]
        out["roads"].append({"id": e["id"], "kind": k, "w": w, "line": line})
    jingu_outer = jingu_inner = None
    for e in load("areas"):
        t = e.get("tags", {})
        if e["type"] == "node" and t.get("natural") == "tree":
            p = xy(e)
            if not in_zone(p):
                out["trees"].append(p)
            continue
        if "geometry" not in e:
            continue
        if t.get("natural") == "tree_row":
            out["tree_rows"].append([xy(p) for p in e["geometry"]])
            continue
        poly = ring(e["geometry"])
        if len(poly) < 3:
            continue
        if e["id"] == 15772082:
            jingu_outer = poly
            continue
        if e["id"] == 126985292:
            jingu_inner = poly
        kind = None
        if t.get("leisure") == "pitch":
            kind = "court" if t.get("sport") == "tennis" else "pitch"
        elif t.get("leisure") in ("park", "garden") or t.get("landuse") in ("grass", "cemetery", "recreation_ground"):
            kind = "lawn"
        elif t.get("landuse") == "forest" or t.get("natural") in ("wood", "scrub"):
            kind = "wood"
        elif t.get("landuse") in ("construction", "brownfield"):
            kind = "dirt"
        elif t.get("leisure") == "swimming_pool" or t.get("natural") == "water":
            kind = "water"
        if kind is None:
            continue
        if e["id"] == 617646450 or in_zone(centroid(poly)) and kind != "wood":
            continue
        out["areas"].append({"id": e["id"], "kind": kind, "poly": poly})
    if jingu_outer:
        out["jingu"] = {"outer": jingu_outer, "inner": jingu_inner}
    with open(os.path.join(ROOT, "config", "surroundings.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    srcs = {}
    for b in out["buildings"]:
        srcs[b["src"]] = srcs.get(b["src"], 0) + 1
    print("建物 %d 棟(高さの出どころ %s、スタジアムの中で除いた %d)、道 %d 本、面 %d、木 %d 本、並木 %d 列、神宮球場 %s" % (
        len(out["buildings"]), srcs, skipped, len(out["roads"]), len(out["areas"]), len(out["trees"]),
        len(out["tree_rows"]), "あり" if out["jingu"] else "なし"))
    for st in out["stadiums"]:
        co, ci = centroid(st["outer"]), centroid(st["inner"])
        ro = (abs(area(st["outer"])) / math.pi) ** 0.5
        ri = (abs(area(st["inner"])) / math.pi) ** 0.5
        print("  競技場 %s %s: 高さ %.1f m、中心 X=%.0f Y=%.0f、外周の半径(面積から)%.0f m、内周 %.0f m(中心のずれ %.1f m)" % (
            st["id"], st["name"] or "(名前なし)", st["h"], co[0], co[1], ro, ri, math.dist(co, ci)))
    tall = sorted(out["buildings"], key=lambda b: -b["h"])[:8]
    for b in tall:
        c = centroid(b["poly"])
        print("  高い: %-22s %5.1f m (%s) 中心 X=%.0f Y=%.0f" % (b["name"] or b["id"], b["h"], b["src"], c[0], c[1]))


main()
