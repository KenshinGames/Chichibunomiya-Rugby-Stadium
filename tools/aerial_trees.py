"""目盛りつきの空中写真(refs/map/grid10m.png、±130 m、1 m = 5 画素)の濃い緑の所に木を置く。
OSM に林として入っていない木(バックスタンドの裏の林など)を補う。結果は config/surroundings.json の "trees_aerial"。

    python3 tools/aerial_trees.py      # osm_surroundings.py のあとに流す

判定: 6 m ごとのます目で、画素の 30% 以上が「緑が赤より 6 以上強く、青より極端に弱くなく、明るさ 135 未満」なら木を 1 本
(この空中写真は青みがかっていて、林は (104,116,105) 前後。屋根・広場・影・テニスコートは 0%、林は 28〜45% だった)。
スタジアムの範囲と、既にある木の 5 m 以内には置かない。乱数の種は固定。
"""
import json
import math
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import osm_surroundings as OS  # noqa: E402

GRID = os.path.join(ROOT, "refs", "map", "grid10m.png")
INFO = json.load(open(os.path.join(ROOT, "refs", "map", "grid_info.json")))
CELL = 6.0


def main():
    W = H = INFO["size_px"]
    ppm = INFO["pixels_per_m"]
    ox, oy = INFO["origin_px"]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", GRID, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    px = lambda x, y: raw[(y * W + x) * 3:(y * W + x) * 3 + 3]
    S = json.load(open(os.path.join(ROOT, "config", "surroundings.json")))
    have = [tuple(p) for p in S["trees"]]
    rnd = random.Random(2026)
    out = []
    half = (W / 2) / ppm - CELL
    n = int(2 * half / CELL)
    for i in range(n):
        for j in range(n):
            X = -half + (i + 0.5) * CELL
            Y = -half + (j + 0.5) * CELL
            if any(OS.in_zone((X + dx, Y + dy)) for dx, dy in ((0, 0), (6, 0), (-6, 0), (0, 6), (0, -6))):
                continue                               # スタンドから 6 m 以内には置かない(葉が客席にかぶる)
            # このます目の画素(格子の黄色い線は飛ばす)
            green = tot = 0
            for a in range(0, int(CELL * ppm), 2):
                for b in range(0, int(CELL * ppm), 2):
                    xx = X - CELL / 2 + a / ppm
                    yy = Y - CELL / 2 + b / ppm
                    c = int(round(ox - yy * ppm)), int(round(oy - xx * ppm))
                    if not (0 <= c[0] < W and 0 <= c[1] < H):
                        continue
                    r, g, bl = px(*c)
                    if r > 200 and g > 200 and bl < 90:
                        continue                       # 目盛りの線
                    tot += 1
                    if g > r + 6 and g >= bl - 4 and (r + g + bl) / 3 < 135:
                        green += 1
            if tot == 0 or green / tot < 0.30:
                continue
            p = (X + rnd.uniform(-1.5, 1.5), Y + rnd.uniform(-1.5, 1.5))
            if any(math.dist(p, q) < 5.0 for q in have):
                continue
            out.append([round(p[0], 1), round(p[1], 1)])
            have.append(p)
    S["trees_aerial"] = out
    S["_comment_trees_aerial"] = "trees_aerial は空中写真(国土地理院)の濃い緑のます目に置いた木(tools/aerial_trees.py)"
    with open(os.path.join(ROOT, "config", "surroundings.json"), "w") as f:
        json.dump(S, f, ensure_ascii=False, separators=(",", ":"))
    print("空中写真から木 %d 本" % len(out))


if __name__ == "__main__":
    main()
