"""⑤座席: 1 脚の形を点の上に並べる(花園と同じ仕組み)。色ごと・スタンドごとに点の集まりを分ける。

色: 西と東の中央(|u| < yellow_u)が黄色、ほかは青(JSC の座席図と写真)。北は座席のない灰色の段。
"""
import bpy

from . import config, layout, materials as M
from .util import MB, coll


def _seat_mesh(name, mat):
    """背もたれつきの座席 1 脚。前(グラウンド側)は -Y。"""
    mb = MB()
    dark = M.get("dark_steel")
    mb.box(-0.21, 0.21, -0.20, 0.20, 0.38, 0.43, mat)
    b0, b1 = 0.20, 0.25
    t = 0.07
    for (z0, z1, s0, s1) in ((0.40, 0.60, 0.0, t * 0.5), (0.60, 0.80, t * 0.5, t)):
        mb.face(((-0.21, b0 + s0, z0), (0.21, b0 + s0, z0), (0.21, b0 + s1, z1), (-0.21, b0 + s1, z1)), mat)
        mb.face(((0.21, b1 + s0, z0), (-0.21, b1 + s0, z0), (-0.21, b1 + s1, z1), (0.21, b1 + s1, z1)), mat)
        for x, fl in ((-0.21, True), (0.21, False)):
            q = ((x, b0 + s0, z0), (x, b1 + s0, z0), (x, b1 + s1, z1), (x, b0 + s1, z1))
            mb.face(tuple(reversed(q)) if fl else q, mat)
    mb.face(((-0.21, b0 + t, 0.80), (0.21, b0 + t, 0.80), (0.21, b1 + t, 0.80), (-0.21, b1 + t, 0.80)), mat)
    mb.box(-0.035, 0.035, 0.02, 0.22, 0.0, 0.38, dark)
    c = coll("seat_proto")
    ob = mb.build(name, c)
    return ob.data


def seat_color(name, u):
    sc = config.load()["seats"]
    if name in ("west", "east") and abs(u) < sc["yellow_u"]:
        return "yellow"
    return "blue"


def seat_points(name):
    """スタンドの席の位置 [(u, d, z)](局所座標)。縦通路、両端、出入口の前後をよける。"""
    sc = config.load()["seats"]
    st = layout.stand(name)
    V = layout.voms(st)
    A = layout.aisles(st)
    pts = []
    for t in layout.treads(st):
        if t["kind"] != "row":
            continue
        d = t["d0"] + 0.45
        a, b = layout.u_range(st, d)
        cuts = [(a - 1, a + sc["edge_w"]), (b - sc["edge_w"], b + 1)]
        for u in A[1:-1]:
            cuts.append((u - sc["aisle_w"] / 2, u + sc["aisle_w"] / 2))
        for v in V:
            if v["d0"] - 1e-6 <= t["d0"] < v["d1"] - 1e-6:
                cuts.append((v["u0"] - 0.35, v["u1"] + 0.35))
        for (x0, x1) in layout.subtract(a, b, cuts):
            n = int((x1 - x0 + 1e-6) // sc["pitch"])
            if n <= 0:
                continue
            off = x0 + ((x1 - x0) - n * sc["pitch"]) / 2 + sc["pitch"] / 2
            for i in range(n):
                pts.append((off + i * sc["pitch"], d, t["z"]))
    return pts


def build():
    c = coll("seats")
    sc = config.load()["seats"]
    meshes = {"blue": _seat_mesh("seat_blue", M.get("seat_blue")),
              "yellow": _seat_mesh("seat_yellow", M.get("seat_yellow"))}
    proto = bpy.data.collections["seat_proto"]
    proto.hide_render = True
    proto.hide_viewport = True
    total = 0
    for name in ("west", "east", "north", "south"):
        if name in sc.get("no_seats", []):
            continue
        pts = seat_points(name)
        total += len(pts)
        groups = {"blue": [], "yellow": []}
        for p in pts:
            groups[seat_color(name, p[0])].append(p)
        print("[seats] %-5s %5d 席(青 %d、黄 %d)" % (name, len(pts), len(groups["blue"]), len(groups["yellow"])))
        for col, plist in groups.items():
            if not plist:
                continue
            me = bpy.data.meshes.new("seatpts_%s_%s" % (name, col))
            me.from_pydata(plist, [], [])
            ob = bpy.data.objects.new(me.name, me)
            ob.matrix_world = layout.xf(name)
            c.objects.link(ob)
            ob.instance_type = "VERTS"
            child = bpy.data.objects.new("seat_%s_%s" % (name, col), meshes[col])
            c.objects.link(child)
            child.parent = ob
    print("[seats] 合計 %d 席(北の段は数えない)" % total)
