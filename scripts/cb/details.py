"""⑤細部: 縦通路の段、出入口の箱、手すり。花園の details.py を秩父宮に合わせて直したもの。

出入口の箱の色は写真から: 青い区画は薄い水色、黄色い区画は薄い黄色、北は赤い枠(写真 Asian Rugby-3、Stadium-w3)。
"""
from . import config, layout, materials as M, seats
from .util import MB, coll


def rail_u(mb, u0, u1, d, z, h=1.1, mat=None, post=1.5):
    """u 方向の手すり(支柱、笠木、中桟)。"""
    mat = mat or M.get("aluminium")
    if u1 - u0 < 0.3:
        return
    n = max(1, round((u1 - u0) / post))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        mb.cyl((u, d, z), (u, d, z + h), 0.022, mat, n=6)
    mb.cyl((u0, d, z + h), (u1, d, z + h), 0.028, mat, n=6)
    mb.cyl((u0, d, z + h * 0.5), (u1, d, z + h * 0.5), 0.016, mat, n=5)


def _vom_mat(name, u):
    if name == "north":
        return M.get("vom_red")
    return M.get("vom_yellow") if seats.seat_color(name, u) == "yellow" else M.get("vom_blue")


def build():
    c = coll("details")
    sc = config.load()["seats"]
    for name in ("west", "east", "north", "south"):
        st = layout.stand(name)
        xf = layout.xf(name)
        T = layout.treads(st)
        V = layout.voms(st)
        A = layout.aisles(st)
        w = sc["aisle_w"]

        # 縦通路: 少し明るいコンクリートの帯と、蹴上げを半分に割る小段
        mb = MB(xf)
        step = M.get("concrete_light")
        for t in T:
            if t["kind"] != "row":
                continue
            a, b = layout.u_range(st, t["d0"])
            lanes = [(u - w / 2, u + w / 2) for u in A[1:-1]]
            lanes += [(a, a + sc["edge_w"]), (b - sc["edge_w"], b)]
            for (l0, l1) in lanes:
                um = (l0 + l1) / 2
                if any(v["u0"] - 0.3 < um < v["u1"] + 0.3 and v["d0"] - 1e-6 <= t["d0"] < v["d1"] - 1e-6 for v in V):
                    continue
                mb.rect(l0, l1, t["d0"], t["d1"] - 0.42, t["z"] + 0.006, step)
                mb.box(l0, l1, t["d1"] - 0.42, t["d1"], t["z"], t["z"] + t["riser"] / 2, step, bottom=False)
        mb.build("aisles_" + name, c)

        # 出入口の箱: 両脇の壁、後ろの壁、上の板、床、奥の暗い口
        mb = MB(xf)
        for v in V:
            m = _vom_mat(name, (v["u0"] + v["u1"]) / 2)
            for (x0, x1) in ((v["u0"] - 0.2, v["u0"]), (v["u1"], v["u1"] + 0.2)):
                mb.box(x0, x1, v["d0"], v["d1"], v["zf"], v["ztop"], m)
            mb.box(v["u0"] - 0.2, v["u1"] + 0.2, v["d1"] - 0.2, v["d1"], v["zf"], v["ztop"], m)
            mb.box(v["u0"] - 0.2, v["u1"] + 0.2, v["d0"] + 0.6, v["d1"], v["ztop"] - 0.12, v["ztop"], m)
            mb.rect(v["u0"], v["u1"], v["d0"], v["d1"] - 0.2, v["zf"] + 0.01, M.get("concrete"))
            mb.box(v["u0"] + 0.35, v["u1"] - 0.35, v["d1"] - 0.23, v["d1"] - 0.2, v["zf"], v["zf"] + 2.2, M.get("black"))
            # ゲート番号の白い札(番号は段階 6)
            mb.box((v["u0"] + v["u1"]) / 2 - 0.35, (v["u0"] + v["u1"]) / 2 + 0.35, v["d1"] - 0.25, v["d1"] - 0.22,
                   v["zf"] + 2.4, v["zf"] + 2.9, M.get("sign_white"))
        if not mb.empty():
            mb.build("voms_" + name, c)

        # 手すり: 前の壁の上、横通路の前
        mb = MB(xf)
        a, b = layout.u_range(st, 0.15)
        rail_u(mb, a + 0.1, b - 0.1, 0.15, st["front_wall_h"])
        flats = [t for t in T if t["kind"] == "flat"]
        mids = flats[1:-1] if T[0]["kind"] == "flat" else flats[:-1]
        for t in mids:
            a, b = layout.u_range(st, t["d0"])
            cuts = [(u - w / 2, u + w / 2) for u in A[1:-1]]
            for (x0, x1) in layout.subtract(a + sc["edge_w"], b - sc["edge_w"], cuts):
                rail_u(mb, x0 + 0.05, x1 - 0.05, t["d0"] + 0.08, t["z"], h=1.0)
        mb.build("rails_" + name, c, smooth=True)
