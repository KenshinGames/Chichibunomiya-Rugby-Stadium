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
        bb = st.get("back_block")
        if name == "west" and bb:
            # 後ろの部屋の下は外壁の吹き抜け(_west_facade)。後ろの壁は斜めの裏面より上だけ、両脇はそのまま
            zs = _soffit_z(st, dE)
            for (p0, p1, za) in ((aE, bb["u0"], 0.0), (bb["u0"], bb["u1"], zs), (bb["u1"], bE, 0.0)):
                if p1 - p0 > 0.05:
                    mb.face(((p1, dE, za), (p0, dE, za), (p0, dE, zprev + ph), (p1, dE, zprev + ph)), wall)
        else:
            mb.face(((bE, dE, 0), (aE, dE, 0), (aE, dE, zprev + ph), (bE, dE, zprev + ph)), wall)
        if ph:
            mb.box(aE, bE, dE - 0.2, dE, zprev, zprev + ph, wall)
    if "_poly" in st:
        _edge_parapets(name, st, mb, ph, wall)
    elif not st.get("corners"):
        _end_walls(st, mb, ph)
        if name in END_WALK:
            _end_walk(st, mb, END_WALK[name])
        if name in FRONT_WALK_EXT:
            _front_walk_ext(st, mb, FRONT_WALK_EXT[name])
    mb.build("stand_" + name, c)


END_WALL = dict(th=0.3, above=1.0, band_h=1.4, band_out=0.25, rail=0.45, post=2.0)


END_WALK = {"north": dict(w=3.2)}
# 写真 018(北西の角の外から): 北スタンドの端の壁ぞいに、外から芝の角へ行く通路があり、外側は柵。
# 南スタンドの前の通路(写真 025)は端の脇ではなく座席の前にあるので、寸法の最前の flat で作り、両端から外へ FRONT_WALK_EXT だけ延ばす。
# 北の通路の高さは模型の地面(芝と同じ高さ)に置いた(写真 018 で段差は見えない)

FRONT_WALK_EXT = {"south": 3.0}   # 写真 025: 前の通路は端の壁より先(メインスタンドとの間)へ続く。長さは推定


def _end_walk(st, mb, cfg):
    """端の壁の外の通路(舗装の帯)と、その外側の網の柵(高さ 1.8 m、2.5 m ごとの柱)。"""
    E = END_WALL
    pave = M.get("paving_grey")
    mesh = M.get("fence_mesh")
    steel = M.get("grey_steel")
    T = layout.treads(st)
    dE = T[-1]["d1"]
    off0 = E["th"] + E["band_out"]
    w = cfg["w"]
    for side, s in ((0, -1.0), (1, 1.0)):
        U = lambda d, o: layout.u_range(st, d)[side] + s * o
        ds = [0.0] + layout.breaks(st, 0.0, dE) + [dE]
        ds = sorted(set(ds))
        for da, db in zip(ds, ds[1:]):
            q = [(U(da, off0), da, 0.03), (U(db, off0), db, 0.03), (U(db, off0 + w), db, 0.03), (U(da, off0 + w), da, 0.03)]
            mb.face(q if s < 0 else q[::-1], pave)
            # 柵: 網の面と上下の横棒
            f = [(U(da, off0 + w), da, 0.0), (U(db, off0 + w), db, 0.0), (U(db, off0 + w), db, 1.8), (U(da, off0 + w), da, 1.8)]
            mb.face(f, mesh)
            for z in (0.05, 1.8):
                mb.cyl((U(da, off0 + w), da, z), (U(db, off0 + w), db, z), 0.025, steel, n=6)
        n = max(1, int(dE / 2.5 + 0.5))
        for i in range(n + 1):
            d = dE * i / n
            mb.cyl((U(d, off0 + w), d, 0.0), (U(d, off0 + w), d, 1.8), 0.035, steel, n=6)


def _front_walk_ext(st, mb, ext):
    """最前の通路を両端から外へ延ばす台(高さは前の壁と同じ)と、芝の側の網の柵。写真 025。"""
    from .details import _front_mesh
    pave, wall = M.get("paving_grey"), M.get("concrete_light")
    T = layout.treads(st)
    z, d1 = T[0]["z"], T[0]["d1"]
    a, b = layout.u_range(st, 0.0)
    for (u0, u1) in ((a - ext, a), (b, b + ext)):
        mb.box(u0, u1, 0.0, d1, 0.0, z, wall, bottom=False)
        mb.face(((u0, 0.0, z + 0.005), (u1, 0.0, z + 0.005), (u1, d1, z + 0.005), (u0, d1, z + 0.005)), pave)
        _front_mesh(mb, u0, u1, 0.15, z)


def _end_walls(st, mb, ph):
    """スタンドの両端の側壁(写真 019・025・018・014・047)。段の外側に厚さ 0.3 m の壁を地面から立て、
    上端は各段の中央から 1.0 m 上を結んだ斜めの線(段々ではなくまっすぐ上がる)。外側の上の縁は 0.25 m 張り出した帯(写真 014・047 の太い縁)、
    上に金属の手すり(写真 019・025)。高さと厚さは写真の座席・人との比からの推定。
    両端が角のブロックにつながるバックスタンド(corners)は折れ目なので作らない(角のブロックの外周は _edge_parapets の手すり)。"""
    E = END_WALL
    conc = M.get("concrete")
    alu = M.get("aluminium")
    T = layout.treads(st)
    dE = T[-1]["d1"]
    # 最前が広い通路(2 m 超)なら、壁は座席の始まりから(写真 025: 前の通路の端は開いている)
    ds0 = T[0]["d1"] if T[0]["kind"] == "flat" and T[0]["d1"] - T[0]["d0"] > 2.0 else 0.0
    # 上端の線: 前の端、各踏み面の中央、後ろの端(後ろの腰壁の高さに合わせる)
    prof = [(ds0, T[0]["z"] + E["above"])]
    prof += [((t["d0"] + t["d1"]) / 2, t["z"] + E["above"]) for t in T if (t["d0"] + t["d1"]) / 2 > ds0 + 1e-6]
    prof += [(dE, T[-1]["z"] + max(ph, E["above"]))]
    # 端の折れ目(平面で端が曲がる所)でも点を足す
    ds = sorted(set([p[0] for p in prof] + [b for b in layout.breaks(st, 0.0, dE) if b > ds0]))

    def top(d):
        for (d0, z0), (d1, z1) in zip(prof, prof[1:]):
            if d0 - 1e-9 <= d <= d1:
                return z0 + (z1 - z0) * (d - d0) / max(1e-9, d1 - d0)
        return prof[-1][1]

    def floor(d):
        for t in T:
            if t["d0"] - 1e-9 <= d <= t["d1"] + 1e-9:
                return t["z"]
        return T[-1]["z"]

    th, bo, bh = E["th"], E["band_out"], E["band_h"]
    for side, s in ((0, -1.0), (1, 1.0)):
        def U(d, off=0.0):
            return layout.u_range(st, d)[side] + s * off
        for da, db in zip(ds, ds[1:]):
            za, zb = top(da), top(db)
            fa, fb = min(floor(da), floor(db)), min(floor(da), floor(db))
            # 内側(客席側)の面: 段の上から上端まで
            q = [(U(da), da, fa), (U(db), db, fb), (U(db), db, zb), (U(da), da, za)]
            mb.face(q if s > 0 else q[::-1], conc)
            # 外側の面: 地面から帯の下まで(帯より奥に引っこむ)
            q = [(U(da, th), da, 0.0), (U(db, th), db, 0.0), (U(db, th), db, zb - bh), (U(da, th), da, za - bh)]
            mb.face(q[::-1] if s > 0 else q, conc)
            # 帯: 外の面、下の面、上の面
            q = [(U(da, th + bo), da, za - bh), (U(db, th + bo), db, zb - bh), (U(db, th + bo), db, zb), (U(da, th + bo), da, za)]
            mb.face(q[::-1] if s > 0 else q, conc)
            q = [(U(da, th), da, za - bh), (U(db, th), db, zb - bh), (U(db, th + bo), db, zb - bh), (U(da, th + bo), da, za - bh)]
            mb.face(q if s > 0 else q[::-1], conc)
            q = [(U(da), da, za), (U(db), db, zb), (U(db, th + bo), db, zb), (U(da, th + bo), da, za)]
            mb.face(q[::-1] if s > 0 else q, conc)
        # 前と後ろの小口
        for d, zt, sg in ((ds0, top(ds0), -1.0), (dE, top(dE), 1.0)):
            u0, u1 = U(d), U(d, th + bo)
            mb.face(((u0, d, 0.0), (u1, d, 0.0), (u1, d, zt), (u0, d, zt)), conc)
        # 手すり: 上端の線の 0.45 m 上、2 m ごとに支柱
        um = lambda d: U(d, th / 2)
        L = dE - ds0
        n = max(2, int(L / E["post"] + 0.5))
        for i in range(n):
            d0, d1 = ds0 + L * i / n, ds0 + L * (i + 1) / n
            mb.cyl((um(d0), d0, top(d0) + E["rail"]), (um(d1), d1, top(d1) + E["rail"]), 0.03, alu, n=6)
            mb.cyl((um(d0), d0, top(d0)), (um(d0), d0, top(d0) + E["rail"]), 0.022, alu, n=6)


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
    # 躯体(地面から部屋の床まで)と部屋の箱。外側(西)の面は _west_facade で作る
    _west_facade(mb, st, u0, u1, d0, d1, z0, wall)
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


FACADE = dict(recess=2.0, low_h=3.6, slab=0.4, void=9.0, band_h=1.8, band_out=1.0, col_step=7.0, col=1.1,
              stair_w=10.0, stair_run=8.0, stair_steps=13, stair_rise=0.277, landing=9.0, panel_w=9.0)
# 写真 413(2019 年、正面から)・031・048・005・724 から。高さは写真の比からの推定(帯の上端 = 部屋の床 + 0.4 m、1 階 3.6 m)。
# 階段は OSM の steps(Y 94→86)と空中写真の白い長方形(Y 77〜93.7)から: 外壁の前 9 m の踊り場と 8 m の階段


def _soffit_z(st, d):
    """外壁の吹き抜けの奥に見える、客席の裏の斜めの面の高さ(d は外壁からの深さの座標)。"""
    F = FACADE
    bb = st["back_block"]
    d1 = bb["d1"]
    z0 = layout.top_z(st)
    za, zb = F["low_h"] + F["slab"], z0 - F["band_h"] + 0.4
    dv = d1 - F["void"]
    t = (d - dv) / max(1e-6, (d1 - 0.6) - dv)
    return za + (zb - za) * max(0.0, min(1.0, t))


def _west_facade(mb, st, u0, u1, d0, d1, z0, wall):
    """メインスタンドの裏(西)の外壁。写真 413・031・048・005・724(正面入場口と広場から見る)。下から:
    1 階(3.6 m)は奥の暗い部屋の列と吹き抜け、その上は柱の間から客席の裏の斜めの面と斜めの梁が見える吹き抜け、
    部屋の階のすぐ下に明るい灰色の帯(柱の位置に明るい四角)、その上に小窓の並ぶ部屋の階の灰色の外壁。
    中央は広い階段が 1 階の上の踊り場へ上がり、奥に縦の筋の入った明るい板と、殿下の像。寸法はすべて推定(FACADE)。"""
    F = FACADE
    dr = d1 - F["recess"]
    dv = d1 - F["void"]
    grey = M.get("facade_grey")
    light = M.get("facade_beige")
    shade = M.get("concourse_dark")
    soffit = M.get("concrete_dark")
    conc = M.get("concrete")
    lh, sl = F["low_h"], F["slab"]
    b1 = z0 + 0.4
    b0 = b1 - F["band_h"]
    # 1 階: 奥の暗い部屋の面、1 階の上の床板(前の縁は外壁の線)
    mb.box(u0, u1, dv, dr, 0.0, lh, wall)
    mb.face(((u1, dr + 0.02, 0.0), (u0, dr + 0.02, 0.0), (u0, dr + 0.02, lh), (u1, dr + 0.02, lh)), shade)
    mb.box(u0, u1, dv, d1 - 0.3, lh, lh + sl, conc)
    mb.face(((u0, dr, lh - 0.01), (u1, dr, lh - 0.01), (u1, d1 - 0.3, lh - 0.01), (u0, d1 - 0.3, lh - 0.01)), shade)
    # 吹き抜けの奥: 客席の裏の斜めの面(外へ向かって上がる)と、両端の壁
    za, zb = _soffit_z(st, dv), _soffit_z(st, d1 - 0.6)
    mb.face(((u1, dv, za), (u0, dv, za), (u0, d1 - 0.6, zb), (u1, d1 - 0.6, zb)), soffit)
    for u in (u0, u1):
        mb.face(((u, dv, lh + sl), (u, d1, lh + sl), (u, d1, b0), (u, dv, za)), wall)
    # 柱(地面から帯まで)と、柱ごとの斜めの梁(客席を支える)
    n = int((u1 - u0) // F["col_step"])
    us = [u0 + 0.6 + (u1 - u0 - 1.2) * i / n for i in range(n + 1)]
    for u in us:
        mb.box(u - F["col"] / 2, u + F["col"] / 2, d1 - F["col"], d1, 0.0, b0, conc)
        mb.cyl((u, dv, za - 0.45), (u, d1 - F["col"], zb - 0.45), 0.42, conc, n=4)
    # 1 階の吹き抜けの天井灯(夜だけ光る)
    lamp = M.emissive("concourse_light", (1.0, 0.84, 0.62, 1.0), 0.0, 9.0, base=(0.8, 0.8, 0.78, 1.0))
    for i in range(n):
        um = (us[i] + us[i + 1]) / 2
        z = lh - 0.04
        mb.face(((um - 1.5, dr + 0.7, z), (um - 1.5, dr + 1.3, z), (um + 1.5, dr + 1.3, z), (um + 1.5, dr + 0.7, z)), lamp)
    # 明るい灰色の帯(外へ張り出す)と、柱の位置の明るい四角
    mb.box(u0 - 0.5, u1 + 0.5, d1 - 0.6, d1 + F["band_out"], b0, b1, grey)
    for u in us:
        mb.box(u - 0.45, u + 0.45, d1 + F["band_out"], d1 + F["band_out"] + 0.04, b0 + 0.45, b1 - 0.45, light)
    # 部屋の階の外の面(灰色)と小窓・換気口
    zt = z0 + st["back_block"]["room_h"]
    mb.box(u0, u1, d1, d1 + 0.05, b1, zt, grey)
    k = int((u1 - u0) // 4.2)
    for i in range(k):
        u = u0 + 2.1 + 4.2 * i
        if i % 3 == 1:
            mb.box(u - 0.5, u + 0.5, d1 + 0.05, d1 + 0.08, b1 + 1.6, b1 + 2.7, shade)     # 小窓
        else:
            mb.box(u - 0.25, u + 0.25, d1 + 0.05, d1 + 0.09, b1 + 2.2, b1 + 2.5, shade)   # 換気口
    # 中央の大階段(外から 1 階の上の踊り場へ)。両脇に腰壁
    w, run, ns, rz = F["stair_w"], F["stair_run"], F["stair_steps"], F["stair_rise"]
    t = run / ns
    ds = d1 + F["landing"]                                       # 階段の上端
    for j in range(ns):
        da = ds + run - (j + 1) * t
        mb.box(-w / 2, w / 2, da, da + t, 0.0, (j + 1) * rz, conc)
    top = ns * rz
    mb.box(-w / 2 - 2.0, w / 2 + 2.0, dr, ds, 0.0, top, conc)   # 上の踊り場(吹き抜けの奥から外へ 9 m)
    for x in (-w / 2 - 0.3, w / 2):
        mb.face(((x, ds + run, 0.0), (x, ds + run, 1.0), (x, ds, top + 1.0), (x, ds, 0.0)), wall)
        mb.face(((x + 0.3, ds, 0.0), (x + 0.3, ds, top + 1.0), (x + 0.3, ds + run, 1.0), (x + 0.3, ds + run, 0.0)), wall)
        mb.face(((x, ds + run, 1.0), (x + 0.3, ds + run, 1.0), (x + 0.3, ds, top + 1.0), (x, ds, top + 1.0)), wall)
    for x0, x1 in ((-w / 2 - 2.3, -w / 2 - 2.0), (w / 2 + 2.0, w / 2 + 2.3)):
        mb.box(x0, x1, d1, ds, top, top + 1.0, wall)                # 踊り場の両脇の腰壁
    mb.box(-w / 2 - 2.0, w / 2 + 2.0, ds - 0.25, ds, top, top + 0.15, wall)
    # 踊り場の奥の縦の筋の入った明るい板(写真 413 の施設名の英文の板)
    pw = F["panel_w"]
    mb.box(-pw / 2, pw / 2, d1 - 0.5, d1 - 0.2, top, b0, light)
    for i in range(int(pw / 0.6) + 1):
        x = -pw / 2 + 0.6 * i
        mb.box(x - 0.04, x + 0.04, d1 - 0.2, d1 - 0.12, top, b0, grey)
    # 殿下の像(台と立像。写真 413・031。大きさは推定)
    bronze = M.get("gate_bronze")
    mb.box(-1.2, -0.4, d1 + 1.2, d1 + 2.0, top, top + 1.3, grey)
    mb.cyl((-0.8, d1 + 1.6, top + 1.3), (-0.8, d1 + 1.6, top + 2.4), 0.22, bronze, n=8)
    mb.cyl((-0.8, d1 + 1.6, top + 2.4), (-0.8, d1 + 1.6, top + 3.05), 0.17, bronze, n=8)


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
