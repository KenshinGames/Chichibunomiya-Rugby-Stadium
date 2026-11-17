"""OpenStreetMap の外形を、グラウンド基準の座標(メートル)に直して表示する。

使い方: python3 tools/osm_measure.py refs/map0/osm.json [--pitch 617646450] [--ids id,id,...] [--near 200]
座標系: 原点=芝の外形(--pitch の way)の中心、+X=長辺方向の北寄り、+Y=+X から左(反時計回りに 90 度)
--ids を省くと、原点から --near m 以内に入る way をすべて出す。

osm.json の取り方(Overpass API。混んでいて落ちるときは別のミラーを使う):
  Q='[out:json][timeout:60];(way(around:250,緯度,経度)[leisure];way(around:250,緯度,経度)[building];);out geom;'
  curl -s --data-urlencode "data=$Q" https://maps.mail.ru/osm/tools/overpass/api/interpreter -o refs/map0/osm.json
"""
import argparse
import json
import math

ap = argparse.ArgumentParser()
ap.add_argument("osm")
ap.add_argument("--pitch", type=int, default=617646450, help="芝の外形の way(秩父宮は leisure=pitch sport=rugby_union)")
ap.add_argument("--ids", default="")
ap.add_argument("--near", type=float, default=200.0)
a = ap.parse_args()

d = json.load(open(a.osm))
els = {e["id"]: e for e in d["elements"] if e["type"] == "way" and "geometry" in e}
pg = els[a.pitch]["geometry"]
LAT0 = sum(p["lat"] for p in pg[:-1]) / (len(pg) - 1)
LON0 = sum(p["lon"] for p in pg[:-1]) / (len(pg) - 1)


def en(p):
    return ((p["lon"] - LON0) * math.cos(math.radians(LAT0)) * 111320.0, (p["lat"] - LAT0) * 110574.0)


pitch = [en(p) for p in pg[:-1]]
best = max((math.dist(pitch[i], pitch[(i + 1) % len(pitch)]), i) for i in range(len(pitch)))
i = best[1]
p0, p1 = pitch[i], pitch[(i + 1) % len(pitch)]
ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
if math.sin(ang) < 0:
    ang += math.pi
ux = (math.cos(ang), math.sin(ang))
uy = (-ux[1], ux[0])


def proj(p, c=(0, 0)):
    return ((p[0] - c[0]) * ux[0] + (p[1] - c[1]) * ux[1], (p[0] - c[0]) * uy[0] + (p[1] - c[1]) * uy[1])


pp = [proj(p) for p in pitch]
cx = (min(p[0] for p in pp) + max(p[0] for p in pp)) / 2
cy = (min(p[1] for p in pp) + max(p[1] for p in pp)) / 2
c = (cx * ux[0] + cy * uy[0], cx * ux[1] + cy * uy[1])
lat_c = LAT0 + c[1] / 110574.0
lon_c = LON0 + c[0] / (math.cos(math.radians(LAT0)) * 111320.0)
print("長辺の方位: 真北から東へ %.1f 度 (+X の向き)" % ((90 - math.degrees(ang)) % 360))
print("芝の外形の中心: lat %.6f lon %.6f" % (lat_c, lon_c))
print("芝の辺の長さ:", " ".join("%.1f" % math.dist(pitch[k], pitch[(k + 1) % len(pitch)]) for k in range(len(pitch))))
ids = [int(s) for s in a.ids.split(",") if s] or list(els)
for wid in ids:
    e = els.get(wid)
    if not e:
        continue
    q = [proj(en(p), c) for p in e["geometry"]]
    if not a.ids and min(math.hypot(*p) for p in q) > a.near:
        continue
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    t = e.get("tags", {})
    name = " ".join("%s=%s" % (k, v) for k, v in t.items()
                    if k in ("name", "leisure", "building", "sport", "height", "layer", "building:levels"))
    print("\n[%d] %s  X[%.1f, %.1f] Y[%.1f, %.1f]  幅X=%.1f 幅Y=%.1f" %
          (wid, name, min(xs), max(xs), min(ys), max(ys), max(xs) - min(xs), max(ys) - min(ys)))
    print("  " + " ".join("(%.1f,%.1f)" % p for p in q))
