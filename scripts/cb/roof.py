"""④屋根と骨組み: メインスタンド(西)と南スタンドの屋根。

どちらも平らな板。メインは上の部屋の前と後ろに並ぶ太い柱が支え、下面に前へ細くなる梁が出る(片持ち)。
南は前の縁の少し後ろに並ぶ細い柱と、後ろの柱が支える。寸法は config の "roof"。
"""
from . import config, layout, materials as M
from .util import MB, coll


def build():
    c = coll("roof")
    roofs = config.load()["roof"]
    for name, r in roofs.items():
        if name.startswith("_"):
            continue
        _roof(name, r, c)


def column_us(r):
    """柱の u の位置(両端を含む)。"""
    n = r["bays"]
    a, b = r["u0"] + 0.8, r["u1"] - 0.8
    return [a + (b - a) * i / n for i in range(n + 1)]


def floor_z(st, d):
    """d の位置の床の高さ(段の外なら一番上の段の高さ)。"""
    for t in layout.treads(st):
        if t["d0"] - 1e-6 <= d < t["d1"]:
            return t["z"]
    return layout.top_z(st)


def beam_bottom(r, d):
    """梁の下端の高さ。前の縁で浅く、柱の位置で深い。柱より後ろは同じ深さ。"""
    zt = r["z_top"] - r["slab"]
    if d >= r["col_d"]:
        return zt - r["beam_depth_col"]
    t = (d - r["d0"]) / (r["col_d"] - r["d0"])
    return zt - (r["beam_depth_front"] + (r["beam_depth_col"] - r["beam_depth_front"]) * t)


def _roof(name, r, c):
    st = layout.stand(name)
    mb = MB(layout.xf(name))
    top = M.get("roof_sheet")
    under = M.get("roof_under")
    edge = M.get("white_paint")
    conc = M.get("concrete")
    u0, u1, d0, d1 = r["u0"], r["u1"], r["d0"], r["d1"]
    zt = r["z_top"]
    # 板(上は屋根材、下は明るい天井)
    mb.box(u0, u1, d0, d1, zt - r["slab"], zt, top)
    mb.rect(u0, u1, d0, d1, zt - r["slab"] - 0.01, under)
    # 前の縁(鼻隠し)と横の縁
    mb.box(u0 - 0.1, u1 + 0.1, d0 - 0.15, d0 + 0.35, zt - r["fascia"], zt + 0.15, edge)
    for u in (u0, u1):
        mb.box(u - 0.12, u + 0.12, d0, d1, zt - r["slab"] - 0.35, zt + 0.1, edge)
    # 梁: 柱ごとに前の縁から後ろの端まで。下端は前ほど浅い
    w = r["beam_w"] / 2
    for u in column_us(r):
        ds = [d0 + 0.35, r["col_d"], d1]
        for (da, db) in zip(ds, ds[1:]):
            za, zb = beam_bottom(r, da), beam_bottom(r, db)
            zs = zt - r["slab"]
            # 側面 2 枚、下面 1 枚、前の小口
            mb.face(((u - w, da, za), (u - w, db, zb), (u - w, db, zs), (u - w, da, zs)), under)
            mb.face(((u + w, db, zb), (u + w, da, za), (u + w, da, zs), (u + w, db, zs)), under)
            mb.face(((u - w, db, zb), (u - w, da, za), (u + w, da, za), (u + w, db, zb)), under)
        mb.face(((u - w, d0 + 0.35, zt - r["slab"]), (u + w, d0 + 0.35, zt - r["slab"]),
                 (u + w, d0 + 0.35, beam_bottom(r, d0 + 0.35)), (u - w, d0 + 0.35, beam_bottom(r, d0 + 0.35))), under)
    # 柱: 前の列と後ろの列。床から梁の下まで
    s = r["col_size"] / 2
    for u in column_us(r):
        for dc in (r["col_d"], r["col_back_d"]):
            zf = floor_z(st, dc)
            mb.box(u - s, u + s, dc - s, dc + s, zf, beam_bottom(r, dc) + 0.05, conc)
    mb.build("roof_" + name, c)
