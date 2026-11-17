"""③スタンドの大きな形: 四方の段の躯体(出入口の穴あき)、メインスタンド後段の上の部屋、南スタンドの後ろの壁。

出入口の箱・縦通路・手すりは details.py、座席は seats.py、屋根は roof.py。
"""
from . import layout, materials as M
from .util import MB, coll

def build():
    c = coll("stands")
    for name in layout.names():
        _mass(name, c)
    _rooms(c)
    _south_back(c)


def _spans(st, d0, d1):
    """d0〜d1 を端の折れ目で分けた区間の一覧。"""
    ds = [d0] + layout.breaks(st, d0, d1) + [d1]
    return list(zip(ds, ds[1:]))


def _pieces(st, d, cuts):
    a, b = layout.u_range(st, d)
    if b - a < 1e-6:
        return []
    return [(p, q) for (p, q) in layout.subtract(a, b, cuts) if q - p > 1e-6]


def _mass(name, c):
    """段(踏み面と蹴上げ)、両脇の壁、後ろの壁。出入口の範囲は踏み面と蹴上げを抜く。"""
    st = layout.stand(name)
    mb = MB(layout.xf(name))
    conc = M.get("concrete")
    wall = M.get("concrete_light")
    T = layout.treads(st)
    V = layout.voms(st)
    zprev = 0.0
    for i, t in enumerate(T):
        d0, d1, z = t["d0"], t["d1"], t["z"]
        dm = (d0 + d1) / 2
        cuts = [(v["u0"], v["u1"]) for v in V if v["d0"] - 1e-6 <= dm < v["d1"]]
        # 蹴上げ(最初の段は前の壁)
        if z > zprev:
            for (p, q) in _pieces(st, d0, cuts):
                mb.face(((p, d0, zprev), (q, d0, zprev), (q, d0, z), (p, d0, z)), wall if i == 0 else conc)
        for (da, db) in _spans(st, d0, d1):
            if layout.width(st, (da + db) / 2) < 1e-6:
                continue                      # 角のブロックで、この深さは平面の外
            A, B = _pieces(st, da, cuts), _pieces(st, db, cuts)
            if not A or not B:                # 多角形の頂点で幅 0 になる側は点にする
                m = layout.u_range(st, da if not A else db)[0]
                A, B = (A or [(m, m)] * len(B)), (B or [(m, m)] * len(A))
            for (pa, qa), (pb, qb) in zip(A, B):
                mb.face(((pa, da, z), (qa, da, z), (qb, db, z), (pb, db, z)), conc)
            aa, ba = layout.u_range(st, da)
            ab, bb = layout.u_range(st, db)
            mb.face(((ba, da, 0), (bb, db, 0), (bb, db, z), (ba, da, z)), wall)
            mb.face(((ab, db, 0), (aa, da, 0), (aa, da, z), (ab, db, z)), wall)
        zprev = z
    dE = T[-1]["d1"]
    aE, bE = layout.u_range(st, dE)
    ph = st.get("back_parapet", 0.0)
    if bE - aE > 0.05:
        mb.face(((bE, dE, 0), (aE, dE, 0), (aE, dE, zprev + ph), (bE, dE, zprev + ph)), wall)
        if ph:
            mb.box(aE, bE, dE - 0.2, dE, zprev, zprev + ph, wall)
    if "_poly" in st:
        _edge_parapets(name, st, mb, ph, wall)
    mb.build("stand_" + name, c)


def _edge_parapets(name, st, mb, ph, wall):
    """角で切った平面の外周のうち、スタンド全体の外に面する辺(端の壁、後ろの角の斜めの辺、角の前の斜めの辺)に
    手すりを立てる(壁にすると写真 01 の撮影位置の前をふさぐ)。高さはその場所の段+1.0 m。
    折れ目(隣と共有する辺)、前の壁、後ろの壁(上で腰壁を作る)には立てない。"""
    from mathutils import Vector
    T = layout.treads(st)
    base = layout.base_name(name)
    P = layout.config.load()["stands"][base]
    to_parent = layout.xf(base).inverted() @ layout.xf(name)
    dE = layout.depth(P)

    def in_whole(u, d):
        q = to_parent @ Vector((u, d, 0.0))
        return 0.0 <= q[1] <= dE and layout._edge(P["u0"], q[1]) <= q[0] <= layout._edge(P["u1"], q[1]), q[1]

    alu = M.get("aluminium")
    poly = st["_poly"]
    n = len(poly)
    for i in range(n):
        (pu, pd), (qu, qd) = poly[i], poly[(i + 1) % n]
        L = ((qu - pu) ** 2 + (qd - pd) ** 2) ** 0.5
        if L < 0.5:
            continue
        mu, md = (pu + qu) / 2, (pd + qd) / 2
        nu, nd = (qd - pd) / L, -(qu - pu) / L
        inside_a, _ = in_whole(mu + nu * 0.6, md + nd * 0.6)
        inside_b, _ = in_whole(mu - nu * 0.6, md - nd * 0.6)
        if inside_a and inside_b:
            continue                          # 折れ目
        _, dpar = in_whole(mu, md)
        if dpar < 0.5 or dpar > dE - 0.3:
            continue                          # 前の壁と後ろの壁
        k = max(1, int(L / 0.9 + 0.5))
        for j in range(k):
            u0, d0 = pu + (qu - pu) * j / k, pd + (qd - pd) * j / k
            u1, d1 = pu + (qu - pu) * (j + 1) / k, pd + (qd - pd) * (j + 1) / k
            dm = (d0 + d1) / 2
            tz = [t for t in T if t["d0"] - 1e-6 <= dm < t["d1"] + 1e-6]
            if not tz:
                continue
            z = tz[0]["z"] + 1.0
            mb.cyl((u0, d0, z), (u1, d1, z), 0.028, alu, n=6)
            if j % 2 == 0:
                mb.cyl((u0, d0, z - 1.0), (u0, d0, z), 0.022, alu, n=6)


def _rooms(c):
    """メインスタンド後段の上の部屋の列(記者席・貴賓席)。前は腰壁と窓の帯、中央は前へ張り出す貴賓席。"""
    st = layout.stand("west")
    bb = st["back_block"]
    mb = MB(layout.xf("west"))
    wall = M.get("concrete_light")
    dark = M.get("concrete_dark")
    glass = M.emissive("room_glass", (1.0, 0.86, 0.66, 1), 0.0, 1.6, base=M.srgb(40, 52, 60))
    d0 = layout.depth(st)
    z0 = layout.top_z(st)
    u0, u1, d1, rh = bb["u0"], bb["u1"], bb["d1"], bb["room_h"]
    df = d0 + 0.6                       # 部屋の前の面
    # 躯体(地面から部屋の床まで)と部屋の箱
    mb.box(u0, u1, d0, d1, 0.0, z0, wall)
    mb.box(u0, u1, df, d1, z0, z0 + rh, dark, bottom=False)
    # 前の面: 腰壁、窓、上の帯
    zs, zw = z0 + 1.3, z0 + rh - 1.0
    mb.box(u0, u1, df - 0.25, df, z0, zs, wall)
    mb.face(((u0, df - 0.05, zs), (u1, df - 0.05, zs), (u1, df - 0.05, zw), (u0, df - 0.05, zw)), glass)
    mb.box(u0, u1, df - 0.25, df, zw, z0 + rh, wall)
    # 窓の縦の桟(2.4 m ごと)
    n = int((u1 - u0) / 2.4)
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        mb.box(u - 0.06, u + 0.06, df - 0.12, df - 0.04, zs, zw, M.get("aluminium"))
    # 中央の貴賓席: 1 段低く、前へ張り出す。前に手すり
    vu0, vu1, dv = -11.0, 11.0, df - 1.8
    mb.box(vu0, vu1, dv, df, z0 - 0.6, z0 + 0.4, wall)
    mb.face(((vu0, dv - 0.02, z0 + 0.4), (vu1, dv - 0.02, z0 + 0.4), (vu1, dv - 0.02, z0 + 2.9), (vu0, dv - 0.02, z0 + 2.9)), glass)
    mb.box(vu0, vu1, dv, df, z0 + 2.9, z0 + 3.4, wall)
    for u in (vu0, vu1):
        mb.box(u - 0.15, u + 0.15, dv, df, z0 + 0.4, z0 + 2.9, wall)
    mb.build("main_rooms", c)


def _south_back(c):
    """南スタンドの後ろの通路と外壁(屋根の後ろの端まで)。"""
    st = layout.stand("south")
    bb = st.get("back_block")
    if not bb:
        return
    mb = MB(layout.xf("south"))
    d0 = layout.depth(st)
    z0 = layout.top_z(st)
    mb.box(bb["u0"], bb["u1"], d0, bb["d1"], 0.0, z0, M.get("concrete_light"))
    mb.box(bb["u0"], bb["u1"], bb["d1"] - 0.25, bb["d1"], z0, z0 + st.get("back_parapet", 1.1), M.get("concrete_light"))
    mb.build("south_back", c)
