"""写真 03 の芝のラインから、カメラ(位置、向き、焦点距離)を最小二乗で解く。純 Python の Nelder-Mead。"""
import math
import sys

W, H = 960, 720
# (直線 X=const 上の点)
VLINES = {0.0: [(485, 390), (455, 505), (460.6, 470), (425, 617)],
          10.0: [(399, 394), (315.6, 470), (265.6, 518.8), (231, 554), (197, 589)],
          -10.0: [(567, 395), (609, 470), (631, 520), (650, 554), (672, 592)]}
# 横の線: (Y, 写真の y, x の範囲)
HL_A = [(-35.0, 390.0, 485), (-30.0, 396.0, 440)]


def cam(p):
    cx, cy, cz, yaw, pitch, lens = p
    f = (math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), -math.sin(pitch))
    r = (f[1], -f[0], 0.0)
    n = math.hypot(r[0], r[1]); r = (r[0] / n, r[1] / n, 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    return (cx, cy, cz), f, r, u, W * lens / 36.0


def proj(c, P):
    C, f, r, u, fp = c
    d = [P[i] - C[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    return (W / 2 + fp * sum(d[i] * r[i] for i in range(3)) / z, H / 2 - fp * sum(d[i] * u[i] for i in range(3)) / z)


def line_dist(c, P0, P1, q):
    a, b = proj(c, P0), proj(c, P1)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    return abs((q[0] - a[0]) * dy - (q[1] - a[1]) * dx) / L


def cost(p, hl):
    c = cam(p)
    s = 0.0
    for X, pts in VLINES.items():
        for q in pts:
            s += line_dist(c, (X, -35, 0), (X, 35, 0), q) ** 2
    for (Y, y, x) in hl:
        s += line_dist(c, (-50, Y, 0), (50, Y, 0), (x, y)) ** 2
    return s


def nm(fun, x0, step, it=4000):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step[j] if j == i else 0) for j in range(n)] for i in range(n)]
    vals = [fun(p) for p in pts]
    for _ in range(it):
        o = sorted(range(n + 1), key=lambda i: vals[i])
        pts = [pts[i] for i in o]; vals = [vals[i] for i in o]
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [cen[j] + (cen[j] - pts[-1][j]) for j in range(n)]; fr = fun(xr)
        if fr < vals[0]:
            xe = [cen[j] + 2 * (cen[j] - pts[-1][j]) for j in range(n)]; fe = fun(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [cen[j] + 0.5 * (pts[-1][j] - cen[j]) for j in range(n)]; fc = fun(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [[pts[0][j] + 0.5 * (p[j] - pts[0][j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [fun(p) for p in pts[1:]]
    i = min(range(n + 1), key=lambda i: vals[i])
    return pts[i], vals[i]


for label, near in (("近い破線 = 5m(Y30) と 15m(Y20)", [(30.0, 568.7, 430), (20.0, 510.6, 450)]),
                    ("近い破線 = 15m(Y20) と Y10?", [(20.0, 568.7, 430), (10.0, 510.6, 450)]),
                    ("近い破線 = 5m(Y30) だけ", [(30.0, 568.7, 430)]),
                    ("近い破線 = 15m(Y20) だけ", [(20.0, 568.7, 430)])):
    hl = HL_A + near
    best = None
    for lens0 in (24, 29, 35):
        for cy0 in (60, 67, 75):
            x0 = [-2.0, cy0, 12.3, 0.0, math.radians(8), lens0]
            p, v = nm(lambda p: cost(p, hl), x0, [1, 3, 1, 0.02, 0.02, 2])
            if best is None or v < best[1]:
                best = (p, v)
    p, v = best
    npt = sum(len(q) for q in VLINES.values()) + len(hl)
    print("%s: rms %.2f px  cam X %.1f Y %.1f Z %.1f  yaw %.2f° pitch %.2f°  lens %.1f mm" % (
        label, math.sqrt(v / npt), p[0], p[1], p[2], math.degrees(p[3]), math.degrees(p[4]), p[5]))
    C, f, r, u, fp = cam(p)
    tgt = [C[i] + f[i] * 127 for i in range(3)]
    print("   見る先(127 m 先) (%.1f, %.1f, %.1f)" % tuple(tgt))
