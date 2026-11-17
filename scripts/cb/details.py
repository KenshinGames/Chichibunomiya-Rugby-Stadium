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


def rail_line(mb, p0, p1, h=1.0, mat=None, post=1.5):
    """p0 から p1(局所座標の床の点、傾いていてよい)に沿う手すり。"""
    mat = mat or M.get("aluminium")
    L = sum((a - b) ** 2 for a, b in zip(p0, p1)) ** 0.5
    if L < 0.3:
        return
    n = max(1, round(L / post))
    for i in range(n + 1):
        q = [a + (b - a) * i / n for a, b in zip(p0, p1)]
        mb.cyl(q, (q[0], q[1], q[2] + h), 0.022, mat, n=6)
    top = [(p0[0], p0[1], p0[2] + h), (p1[0], p1[1], p1[2] + h)]
    mb.cyl(top[0], top[1], 0.028, mat, n=6)


VOM_DROP = 1.2      # 出入口の床は横通路から奥へ下がる(奥の口の高さを取るため。推定)


def _vom_mat(name, u):
    if layout.base_name(name) == "north":
        return M.get("vom_red")
    return M.get("vom_yellow") if seats.seat_color(name, u) == "yellow" else M.get("vom_blue")


def _gate_no(c, xf, v, zn, name):
    """出入口の白い札にゲート番号(JSC の座席案内の番号)。"""
    from mathutils import Vector
    from .util import text_obj
    if v.get("no") is None:
        return
    um = (v["u0"] + v["u1"]) / 2
    p = xf @ Vector((um, v["d1"] - 0.185, zn + 0.5))
    nrm = (xf.to_3x3() @ Vector((0, -1, 0))).normalized()
    text_obj("gate_no_%s_%d" % (name, v["no"]), str(v["no"]), 0.26, M.get("text_dark"), c, p, nrm)


def _vom(mb, name, T, v):
    """出入口: 横通路の後ろの段を切った上の開いた穴。両脇は段ごとの低いコンクリートの壁(段+0.9 m)と手すり、
    床は奥へ下がり、奥の壁に暗い口と色の枠、口の上の手すりにゲート番号の札。写真 Rugby2・Stadium-4・03。"""
    conc, wall = M.get("concrete"), M.get("concrete_light")
    col = _vom_mat(name, (v["u0"] + v["u1"]) / 2)
    if layout.base_name(name) == "north":
        wall = col                     # 北スタンドの出入口は両脇と奥の壁まで赤く塗ってある(写真 Stadium-w3)
    u0, u1, d0, d1, zf = v["u0"], v["u1"], v["d0"], v["d1"], v["zf"]
    zb = zf - VOM_DROP
    rows = [t for t in T if d0 - 1e-6 <= t["d0"] < d1 - 1e-6]
    nxt = [t for t in T if t["d0"] >= d1 - 1e-6]
    zn = nxt[0]["z"] if nxt else rows[-1]["z"] + rows[-1]["riser"]
    mb.face(((u0, d0, zf + 0.01), (u1, d0, zf + 0.01), (u1, d1 - 0.2, zb), (u0, d1 - 0.2, zb)), conc)
    for t in rows:
        top = t["z"] + 0.9
        mb.box(u0 - 0.2, u0, t["d0"], t["d1"], zb, top, wall)
        mb.box(u1, u1 + 0.2, t["d0"], t["d1"], zb, top, wall)
    for u in (u0 - 0.1, u1 + 0.1):
        rail_line(mb, (u, d0 + 0.1, rows[0]["z"] + 0.9), (u, d1 - 0.1, rows[-1]["z"] + 0.9), h=0.5)
    # 奥の壁と口
    mb.box(u0 - 0.2, u1 + 0.2, d1 - 0.2, d1, zb, zn, wall)
    hm = min(2.3, zn - zb - 0.35)
    mb.box(u0 + 0.35, u1 - 0.35, d1 - 0.23, d1 - 0.2, zb, zb + hm, M.get("black"))
    for (x0, x1) in ((u0 + 0.15, u0 + 0.35), (u1 - 0.35, u1 - 0.15)):
        mb.box(x0, x1, d1 - 0.26, d1 - 0.2, zb, zb + hm + 0.2, col)
    mb.box(u0 + 0.15, u1 - 0.15, d1 - 0.26, d1 - 0.2, zb + hm, zb + hm + 0.2, col)
    # 口の上: 後ろの列の前の手すりと、ゲート番号の札
    rail_u(mb, u0 - 0.2, u1 + 0.2, d1 - 0.1, zn, h=0.9)
    um = (u0 + u1) / 2
    mb.box(um - 0.4, um + 0.4, d1 - 0.16, d1 - 0.12, zn + 0.25, zn + 0.75, col)
    mb.box(um - 0.32, um + 0.32, d1 - 0.17, d1 - 0.16, zn + 0.31, zn + 0.69, M.get("sign_white"))


def build():
    c = coll("details")
    sc = config.load()["seats"]
    for name in layout.names():
        st = layout.stand(name)
        xf = layout.xf(name)
        T = layout.treads(st)
        V = layout.voms(st)
        AU = layout.aisle_us(st)
        w, ew = sc["aisle_w"], sc["edge_w"]

        # 縦通路: 少し明るいコンクリートの帯と、蹴上げを半分に割る小段。端の通路は斜めの縁に沿わせる
        mb = MB(xf)
        step = M.get("concrete_light")
        for t in T:
            if t["kind"] != "row":
                continue
            dA, dB = t["d0"], t["d1"] - 0.42
            a0, b0 = layout.u_range(st, dA)
            a1, b1 = layout.u_range(st, dB)
            if min(b0 - a0, b1 - a1) < 2 * ew + 0.5:
                continue
            lanes = [((u - w / 2, u + w / 2), (u - w / 2, u + w / 2)) for u in AU
                     if a0 + ew < u < b0 - ew and a1 + ew < u < b1 - ew]
            lanes += [((a0, a0 + ew), (a1, a1 + ew)), ((b0 - ew, b0), (b1 - ew, b1))]
            for (l0a, l1a), (l0b, l1b) in lanes:
                um = (l0a + l1a) / 2
                if any(v["u0"] - 0.3 < um < v["u1"] + 0.3 and v["d0"] - 1e-6 <= t["d0"] < v["d1"] - 1e-6 for v in V):
                    continue
                zl = t["z"] + 0.006
                mb.face(((l0a, dA, zl), (l1a, dA, zl), (l1b, dB, zl), (l0b, dB, zl)), step)
                mb.box(l0b, l1b, dB, t["d1"], t["z"], t["z"] + t["riser"] / 2, step, bottom=False)
        if not mb.empty():
            mb.build("aisles_" + name, c)

        # 出入口
        mb = MB(xf)
        for v in V:
            _vom(mb, name, T, v)
            nxt = [t for t in T if t["d0"] >= v["d1"] - 1e-6]
            _gate_no(c, xf, v, nxt[0]["z"] if nxt else v["ztop"], name)
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
            if b - a < 2 * ew + 0.5:
                continue
            cuts = [(u - w / 2, u + w / 2) for u in AU]
            for (x0, x1) in layout.subtract(a + ew, b - ew, cuts):
                rail_u(mb, x0 + 0.05, x1 - 0.05, t["d0"] + 0.08, t["z"], h=1.0)
        if not mb.empty():
            mb.build("rails_" + name, c, smooth=True)
