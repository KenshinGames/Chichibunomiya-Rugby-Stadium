"""③スタンドの大きな形: 四方の段の躯体、出入口の箱、メインスタンド後ろの部屋の列、屋根の板と仮の柱。

細部(座席、手すり、通路の色、屋根の骨組み)は段階 4・5 で足す。
"""
from . import config, layout, materials as M
from .util import MB, coll

STANDS = ("west", "east", "north", "south")


def build():
    c = coll("stands")
    for name in STANDS:
        _mass(name, c)
        _voms(name, c)
    _back_blocks(c)
    _roofs(c)


def _spans(st, d0, d1):
    """d0〜d1 を端の折れ目で分けた区間の一覧。"""
    ds = [d0] + layout.breaks(st, d0, d1) + [d1]
    return list(zip(ds, ds[1:]))


def _mass(name, c):
    """段(踏み面と蹴上げ)、両脇の壁、後ろの壁。床下は地面まで埋まった形として側壁で閉じる。"""
    st = layout.stand(name)
    mb = MB(layout.xf(name))
    conc = M.get("concrete")
    wall = M.get("concrete_light")
    T = layout.treads(st)
    zprev = 0.0
    for i, t in enumerate(T):
        d0, d1, z = t["d0"], t["d1"], t["z"]
        a0, b0 = layout.u_range(st, d0)
        # 蹴上げ(最初の段は前の壁)
        if z > zprev:
            mb.face(((a0, d0, zprev), (b0, d0, zprev), (b0, d0, z), (a0, d0, z)), wall if i == 0 else conc)
        for (da, db) in _spans(st, d0, d1):
            aa, ba = layout.u_range(st, da)
            ab, bb = layout.u_range(st, db)
            mb.face(((aa, da, z), (ba, da, z), (bb, db, z), (ab, db, z)), conc)
            # 両脇の壁(地面から踏み面まで)
            mb.face(((ba, da, 0), (bb, db, 0), (bb, db, z), (ba, da, z)), wall)
            mb.face(((ab, db, 0), (aa, da, 0), (aa, da, z), (ab, db, z)), wall)
        zprev = z
    dE = T[-1]["d1"]
    aE, bE = layout.u_range(st, dE)
    ph = st.get("back_parapet", 0.0)
    mb.face(((bE, dE, 0), (aE, dE, 0), (aE, dE, zprev + ph), (bE, dE, zprev + ph)), wall)
    if ph:
        mb.box(aE, bE, dE - 0.2, dE, zprev, zprev + ph, wall)
    mb.build("stand_" + name, c)


def _voms(name, c):
    """出入口(横通路の後ろに食い込む箱)。前の面は暗い開口。"""
    st = layout.stand(name)
    V = layout.voms(st)
    if not V:
        return
    mb = MB(layout.xf(name))
    wall = M.get("concrete_light")
    dark = M.get("black")
    for v in V:
        u0, u1, d0, d1 = v["u0"], v["u1"], v["d0"], v["d1"]
        zf, zt = v["zf"], v["ztop"]
        mb.box(u0 - 0.25, u1 + 0.25, d0, d1, zf, zt, wall, bottom=False)
        # 開口(前の面の少し手前に暗い板)
        mb.face(((u0, d0 - 0.02, zf), (u1, d0 - 0.02, zf), (u1, d0 - 0.02, zt - 0.6), (u0, d0 - 0.02, zt - 0.6)), dark)
    mb.build("voms_" + name, c)


def _back_blocks(c):
    """メインスタンド後段の上の部屋の列(記者席・貴賓席)と、南スタンドの後ろの通路と外壁。"""
    for name in ("west", "south"):
        st = layout.stand(name)
        bb = st.get("back_block")
        if not bb:
            continue
        mb = MB(layout.xf(name))
        wall = M.get("concrete_light")
        d0 = layout.depth(st)
        z0 = layout.top_z(st)
        u0, u1 = bb["u0"], bb["u1"]
        rh = bb.get("room_h", 0.0)
        # 躯体(地面から部屋の床まで)
        mb.box(u0, u1, d0, bb["d1"], 0.0, z0 + (0.0 if rh else st.get("back_parapet", 1.1)), wall)
        if rh:
            # 部屋: 前面はガラス、上は屋根の下まで
            mb.box(u0, u1, d0 + 0.6, bb["d1"], z0, z0 + rh, wall, bottom=False)
            mb.face(((u0, d0 + 0.58, z0 + 1.0), (u1, d0 + 0.58, z0 + 1.0), (u1, d0 + 0.58, z0 + rh - 0.5),
                     (u0, d0 + 0.58, z0 + rh - 0.5)), M.get("glass_dark"))
        mb.build("back_block_" + name, c)


def _roofs(c):
    """屋根は板と仮の柱だけ(段階 4 で骨組みを作り直す)。"""
    roofs = config.load()["roof"]
    for name, r in roofs.items():
        if name.startswith("_"):
            continue
        st = layout.stand(name)
        mb = MB(layout.xf(name))
        z0, z1 = r["z_bottom"], r["z_bottom"] + r["thickness"]
        mb.box(r["u0"], r["u1"], r["d0"], r["d1"], z0, z1, M.get("roof_under"))
        # 仮の柱: 後ろの端の内側に等間隔。床はその d の踏み面の高さ
        n = max(2, int(round((r["u1"] - r["u0"]) / 10.0)))
        dcol = r["d1"] - 0.6
        zf = _floor_z(st, dcol)
        for k in range(n + 1):
            u = r["u0"] + 0.5 + (r["u1"] - r["u0"] - 1.0) * k / n
            mb.box(u - 0.35, u + 0.35, dcol - 0.35, dcol + 0.35, zf, z0, M.get("concrete"))
        mb.build("roof_" + name, c)


def _floor_z(st, d):
    """d の位置の床の高さ。段の外なら一番上の段の高さ(部屋があればその床)。"""
    for t in layout.treads(st):
        if t["d0"] <= d < t["d1"]:
            return t["z"]
    bb = st.get("back_block")
    z = layout.top_z(st)
    if bb and bb.get("room_h"):
        return z + bb["room_h"]
    return z
