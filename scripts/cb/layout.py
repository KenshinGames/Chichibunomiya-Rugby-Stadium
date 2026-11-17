"""スタンドの断面を段の一覧に直す。stands.py と seats.py が共通で使う。

角のブロック: dimensions.json のスタンドに "corners" があると、両端を折れ目(二等分線)で切り、
その先を「同じ断面を alpha 度回した仮のスタンド」<名前>_c0(u0 の端)と <名前>_c1(u1 の端)として作る。
段の高さは折れ目でちょうどつながる。仮のスタンドの平面は凸多角形 "_poly"(自分の局所座標)で切る。
"""
import math

from mathutils import Matrix

from . import config
from .util import stand_xf

_cache = {}


def names():
    """作るスタンドの名前(角のブロックを含む)。"""
    out = []
    for n, st in config.load()["stands"].items():
        if not isinstance(st, dict) or "side" not in st:
            continue
        out.append(n)
        if "corners" in st:
            out += [n + "_c0", n + "_c1"]
    return out


def base_name(name):
    return name.split("_c")[0]


def stand(name):
    if name not in _cache:
        S = config.load()["stands"]
        if name in S:
            st = S[name]
            if "corners" in st:
                st = dict(st)
                poly = plan_poly(st)
                for k in (0, 1):
                    poly = _clip(poly, lambda p, k=k: -_beyond(st, k, p))
                st["_poly"] = poly
        else:
            st = _corner(name)
        _cache[name] = st
    return _cache[name]


def _frame(st, k):
    """角のブロック k(0=u0 の端、1=u1 の端)の原点(親の u, d)と回転角(rad)。"""
    C = st["corners"]
    a = math.radians(C["alpha_deg"])
    sg = -1 if k == 0 else 1
    return (sg * C["u_c"], 0.0), -sg * a


def _beyond(st, k, p):
    """点 p(親の u, d)が折れ目より端の側なら正。折れ目は (±u_c, 0) から外へ alpha/2 傾いた線。"""
    C = st["corners"]
    sg = -1 if k == 0 else 1
    t = math.tan(math.radians(C["alpha_deg"]) / 2)
    return sg * p[0] - C["u_c"] - p[1] * t


def _corner(name):
    base = base_name(name)
    k = int(name[-1])
    P = config.load()["stands"][base]
    C = P["corners"]
    (ou, od), th = _frame(P, k)
    poly = _clip(plan_poly(P), lambda p: _beyond(P, k, p))
    c, s = math.cos(-th), math.sin(-th)
    local = [((u - ou) * c - (d - od) * s, (u - ou) * s + (d - od) * c) for (u, d) in poly]
    sg = -1 if k == 0 else 1
    st = {key: P[key] for key in ("side", "wall", "segments", "front_wall_h", "back_parapet") if key in P}
    st.update(u0=[[0.0, -1e4]], u1=[[0.0, 1e4]], _poly=local, _base=base, _k=k,
              aisle_us=[sg * u for u in C.get("aisle_us", [])],
              voms=[{"seg": C["vom_seg"], "us": [sg * u for u in C.get("vom_us", [])]}] if C.get("vom_us") else [])
    return st


def xf(name):
    st = stand(name)
    m = stand_xf(st["side"], st["wall"])
    if "_k" in st:
        (ou, od), th = _frame(config.load()["stands"][st["_base"]], st["_k"])
        m = m @ Matrix.Translation((ou, od, 0.0)) @ Matrix.Rotation(th, 4, "Z")
    return m


def plan_poly(st):
    """スタンドの平面の外形 [(u, d)](u1 の側を前から後ろへ、u0 の側を後ろから前へ)。"""
    dE = depth(st)
    ds = sorted(set([0.0, dE] + [p[0] for k in ("u0", "u1") if isinstance(st[k][0], (list, tuple))
                                 for p in st[k] if 0.0 < p[0] < dE]))
    return [(_edge(st["u1"], d), d) for d in ds] + [(_edge(st["u0"], d), d) for d in reversed(ds)]


def _clip(poly, f):
    """多角形のうち f(p) >= 0 の側を残す(Sutherland-Hodgman)。"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = f(p), f(q)
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _poly_span(poly, d):
    xs = []
    n = len(poly)
    for i in range(n):
        (pu, pd), (qu, qd) = poly[i], poly[(i + 1) % n]
        if min(pd, qd) - 1e-9 <= d <= max(pd, qd) + 1e-9:
            if abs(qd - pd) < 1e-9:
                xs += [pu, qu]
            else:
                xs.append(pu + (qu - pu) * (d - pd) / (qd - pd))
    return (min(xs), max(xs)) if xs else None


def treads(st):
    """前から順に、踏み面の一覧 [{d0, d1, z, kind('row'|'flat'), seg, row}]。"""
    d = 0.0
    z = st["front_wall_h"]
    out = []
    for si, seg in enumerate(st["segments"]):
        k = seg[0]
        if k == "rows":
            _, n, t, r = seg
            for i in range(n):
                out.append(dict(d0=d, d1=d + t, z=z, kind="row", seg=si, row=i, riser=r))
                d += t
                z += r
        elif k == "flat":
            out.append(dict(d0=d, d1=d + seg[1], z=z, kind="flat", seg=si, row=0, riser=0.0))
            d += seg[1]
        elif k == "rise":
            z += seg[1]
    return out


def _edge(pts, d):
    """端の位置。pts は [[d, u], ...](d の小さい順)。間は直線、外は端の値。
    花園のひな形の [a, b](u = a + b*d)の書き方も受ける。"""
    if not isinstance(pts[0], (list, tuple)):
        return pts[0] + pts[1] * d
    if d <= pts[0][0]:
        return pts[0][1]
    for (d0, u0), (d1, u1) in zip(pts, pts[1:]):
        if d <= d1:
            return u0 + (u1 - u0) * (d - d0) / (d1 - d0) if d1 > d0 else u1
    return pts[-1][1]


def u_range(st, d):
    """深さ d での左右の端。角のブロックで線が平面にかからないときは (m, m) の幅 0 を返す。"""
    a, b = _edge(st["u0"], d), _edge(st["u1"], d)
    poly = st.get("_poly")
    if poly:
        sp = _poly_span(poly, d)
        if sp is None:
            return (0.0, 0.0)
        a, b = max(a, sp[0]), min(b, sp[1])
    if b < a:
        a = b = (a + b) / 2
    return a, b


def width(st, d):
    a, b = u_range(st, d)
    return b - a


def breaks(st, d0, d1):
    """d0〜d1 の間にある端の折れ目の d(段の面を折れ目で分けるため)。"""
    out = []
    for k in ("u0", "u1"):
        pts = st[k]
        if isinstance(pts[0], (list, tuple)):
            out += [p[0] for p in pts if d0 + 1e-6 < p[0] < d1 - 1e-6]
    out += [p[1] for p in st.get("_poly", []) if d0 + 1e-6 < p[1] < d1 - 1e-6]
    return sorted(set(out))


def depth(st):
    return treads(st)[-1]["d1"]


def top_z(st):
    return treads(st)[-1]["z"]


def aisle_us(st):
    """縦通路の中心の u(両端は含まない)。"aisle_us" があればそれ、なければ前の端(角で切る前)を aisles 等分。"""
    if "aisle_us" in st:
        return list(st["aisle_us"])
    n = st.get("aisles", 0)
    a, b = _edge(st["u0"], 0.0), _edge(st["u1"], 0.0)
    return [a + (b - a) * i / n for i in range(1, n)] if n else []


def voms(st):
    """出入口(ボミトリー)の一覧 [{u0, u1, d0, d1, zf, ztop}]。横通路の後ろに食い込む箱。"""
    sc = config.load()["seats"]
    T = treads(st)
    out = []
    for v in st.get("voms", []):
        flat = [t for t in T if t["seg"] == v["seg"]][0]
        rows = [t for t in T if t["d0"] >= flat["d1"] - 1e-6][:sc["vom_rows"]]
        for u in v["us"]:
            out.append(dict(u0=u - sc["vom_w"] / 2, u1=u + sc["vom_w"] / 2, d0=flat["d1"], d1=rows[-1]["d1"],
                            zf=flat["z"], ztop=rows[-1]["z"] + rows[-1]["riser"] + 1.1))
    return out


def subtract(a, b, cuts):
    """区間 [a, b] から cuts の区間を除いた残り。"""
    out = [(a, b)]
    for (c0, c1) in sorted(cuts):
        nxt = []
        for (x0, x1) in out:
            if c1 <= x0 or c0 >= x1:
                nxt.append((x0, x1))
            else:
                if c0 > x0:
                    nxt.append((x0, c0))
                if c1 < x1:
                    nxt.append((c1, x1))
        out = nxt
    return out
