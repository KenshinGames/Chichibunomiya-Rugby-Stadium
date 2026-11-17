"""スタンドの断面を段の一覧に直す。stands.py と seats.py が共通で使う。"""
from . import config
from .util import stand_xf


def stand(name):
    return config.load()["stands"][name]


def xf(name):
    st = stand(name)
    return stand_xf(st["side"], st["wall"])


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
    return _edge(st["u0"], d), _edge(st["u1"], d)


def breaks(st, d0, d1):
    """d0〜d1 の間にある端の折れ目の d(段の面を折れ目で分けるため)。"""
    out = []
    for k in ("u0", "u1"):
        pts = st[k]
        if isinstance(pts[0], (list, tuple)):
            out += [p[0] for p in pts if d0 + 1e-6 < p[0] < d1 - 1e-6]
    return sorted(set(out))


def depth(st):
    return treads(st)[-1]["d1"]


def top_z(st):
    return treads(st)[-1]["z"]


def aisles(st):
    """縦通路の中心の u(d=0 での位置)。両端も含む。"""
    n = st.get("aisles", 0)
    a, b = u_range(st, 0.0)
    return [a + (b - a) * i / n for i in range(n + 1)] if n else []


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
