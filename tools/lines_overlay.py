"""写真に、模型のラインと目印をカメラで投影して描く(カメラ合わせ用)。
python3 lines_overlay.py photo.jpg out.png cx cy cz tx ty tz lens
"""
import math
import subprocess
import sys

photo, out = sys.argv[1], sys.argv[2]
cx, cy, cz, tx, ty, tz, lens = map(float, sys.argv[3:10])
W, H = (int(sys.argv[10]), int(sys.argv[11])) if len(sys.argv) > 11 else (960, 720)
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", photo, "-vf", "scale=%d:%d" % (W, H),
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
img = bytearray(raw)

C = (cx, cy, cz)
f = [tx - cx, ty - cy, tz - cz]
n = math.sqrt(sum(v * v for v in f)); f = [v / n for v in f]
r = [f[1], -f[0], 0.0]
n = math.sqrt(sum(v * v for v in r)); r = [v / n for v in r]
u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
fp = W * lens / 36.0


def proj(p):
    d = [p[i] - C[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    if z < 0.5:
        return None
    return (W / 2 + fp * sum(d[i] * r[i] for i in range(3)) / z, H / 2 - fp * sum(d[i] * u[i] for i in range(3)) / z)


def put(x, y, col):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < W and 0 <= y < H:
        k = (y * W + x) * 3
        img[k:k + 3] = bytes(col)


def seg(p, q, col, steps=400):
    for i in range(steps + 1):
        t = i / steps
        a = proj([p[j] + (q[j] - p[j]) * t for j in range(3)])
        if a:
            put(*a, col)
            put(a[0], a[1] + 1, col)


RED, CY, YEL, MAG = (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 0, 255)
for y in (35, -35):
    seg((-66, y, 0), (66, y, 0), RED)                 # タッチライン
for y in (30, -30, 20, -20):
    seg((-50, y, 0), (50, y, 0), CY)                  # 5 m・15 m
for x in (0, 10, -10, 28, -28, 50, -50):
    seg((x, -35, 0), (x, 35, 0), RED if x in (0, 50, -50, 28, -28) else CY)
# 南スタンドの断面の線(模型の値): 前の壁の上、横通路の前と後ろ、最上段、屋根の前の縁の下と上、柱
GRN = (0, 255, 0)
for (x, z, col) in ((-73.3, 1.2, GRN), (-78.7, 3.36, GRN), (-80.2, 3.36, GRN), (-90.6, 9.6, GRN),
                    (-78.7, 13.6, MAG), (-78.7, 14.2, MAG)):
    seg((x, -36.4, z), (x, 36.5, z), col)
for k in range(9):
    yy = -37.3 + 74.6 * k / 8
    seg((-79.5, yy, 3.36), (-79.5, yy, 13.3), GRN)
# ゴールポスト(X=±50、Y=±2.8、高さ 12 m、クロスバー 3 m)
for gx in (50, -50):
    for gy in (2.8, -2.8):
        seg((gx, gy, 0), (gx, gy, 12), YEL)
    seg((gx, -2.8, 3), (gx, 2.8, 3), YEL)
# 北の前の壁(X=70.5)、映像装置(X=86、Y 7〜−9、8.4〜17.2 m)
seg((70.5, -33, 1.0), (70.5, 35.7, 1.0), MAG)
for (y0, y1, z0, z1) in ((7, -9, 8.4, 8.4), (7, -9, 17.2, 17.2), (7, 7, 8.4, 17.2), (-9, -9, 8.4, 17.2)):
    seg((86, y0, z0), (86, y1, z1), MAG)
# 東の前の壁(Y=-41.7、上端 1.2 m)と最上部(Y=-76.4、11.2 m)、照明塔の頭
seg((-70, -41.7, 1.2), (70, -41.7, 1.2), YEL)
seg((-70, -41.7, 0.1), (70, -41.7, 0.1), YEL)
for z in (11.2, 12.3):
    seg((-78, -76.4, z), (78, -76.4, z), MAG)
for (x, y, h) in ((45, -82, 25), (-58, -82, 25)):
    seg((x, y, 0), (x, y, h), MAG)

subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
                "-i", "-", out], input=bytes(img), check=True)
print("ok", out)
