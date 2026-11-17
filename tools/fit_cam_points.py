"""既知の 3D 点と写真の点から、カメラ(位置、yaw、pitch、roll、焦点距離)を最小二乗で解く。"""
import math, sys
src = open("fit_cam.py").read()
ns = {}; exec(src.split("def cam(p):")[0] + "def nm" + src.split("def nm")[1].split("for label, near in")[0], ns)
nm = ns["nm"]
W, H = 960, 717
OBS = [  # (X, Y, Z) -> (x, y)   写真 04
    ((-50, 2.8, 12.0), (389.5, 103.5)), ((-50, 2.8, 0.0), (385, 390)),
    ((-50, -2.8, 12.0), (529.5, 109)), ((-50, -2.8, 0.0), (518, 396)),
    ((-50, 2.8, 3.0), (390, 325)), ((-50, -2.8, 3.0), (517.5, 328.5)),
    ((50, 2.8, 0.0), (456, 282)), ((50, -2.8, 0.0), (493.5, 283)),
    ((50, 2.8, 12.0), (456, 205)), ((50, -2.8, 12.0), (493.5, 205)),
]
def cam(p):
    cx, cy, cz, yaw, pitch, roll, lens = p
    f = (math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), -math.sin(pitch))
    r = (f[1], -f[0], 0.0); n = math.hypot(r[0], r[1]); r = (r[0] / n, r[1] / n, 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    cr, sr = math.cos(roll), math.sin(roll)
    r2 = tuple(r[i] * cr + u[i] * sr for i in range(3)); u2 = tuple(u[i] * cr - r[i] * sr for i in range(3))
    return (cx, cy, cz), f, r2, u2, W * lens / 36.0
def proj(c, P):
    C, f, r, u, fp = c
    d = [P[i] - C[i] for i in range(3)]; z = sum(d[i] * f[i] for i in range(3))
    return (W / 2 + fp * sum(d[i] * r[i] for i in range(3)) / z, H / 2 - fp * sum(d[i] * u[i] for i in range(3)) / z)
def cost(p):
    c = cam(p); s = 0
    for P, q in OBS:
        a = proj(c, P); s += (a[0] - q[0]) ** 2 + (a[1] - q[1]) ** 2
    return s
XF = float(sys.argv[1]) if len(sys.argv) > 1 else None
NEAR_ONLY = len(sys.argv) > 2
if NEAR_ONLY:
    OBS[:] = OBS[:6]
best = None
for lens in (27, 29, 32):
    if XF is None:
        p, v = nm(cost, [-84, -1.0, 7.0, 0.05, math.radians(5), 0.0, lens], [3, 2, 2, 0.03, 0.03, 0.02, 3], 6000)
    else:
        f6 = lambda q: cost([XF] + q)
        q, v = nm(f6, [-1.0, 6.0, 0.05, math.radians(5), 0.0, lens], [2, 2, 0.03, 0.03, 0.02, 3], 6000)
        p = [XF] + q
    if best is None or v < best[1]: best = (p, v)
p, v = best
print("rms %.2f px  cam (%.1f, %.1f, %.1f) yaw %.2f° pitch %.2f° roll %.2f° lens %.1f mm" % (
    math.sqrt(v / len(OBS)), p[0], p[1], p[2], math.degrees(p[3]), math.degrees(p[4]), math.degrees(p[5]), p[6]))
c = cam(p)
print("見る先 (%.1f, %.1f, %.1f)" % tuple(c[0][i] + c[1][i] * 120 for i in range(3)))
for name, P in (("映像装置の中心(Y=-1)", (86, -1, 12.8)), ("映像装置の西端 Y=7", (86, 7, 12.8)), ("東端 Y=-9", (86, -9, 12.8))):
    print(name, "→ x %.0f y %.0f" % proj(c, P))
# 写真の映像装置: x 440〜521、中心 480.5、y 189〜230
lo, hi = -40.0, 40.0
for _ in range(60):
    m = (lo + hi) / 2
    if proj(c, (86, m, 12.8))[0] > 480.5: lo = m
    else: hi = m
print("写真の映像装置の中心は Y = %.1f(X=86 とすると)" % m)
