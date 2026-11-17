"""参考写真と同じ角度から描いて、左右に並べた比較画像を docs/compare/ に作る。

  blender -b build/chichibu.blend -P scripts/compare.py -- [--only 01,05] [--samples 96]
左が参考写真(Wikimedia Commons)、右がこのモデル。refs/commons/ に写真がなければ描いた側だけを out/compare/ に残す。
"""
import argparse
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from cb import cameras, config, sky  # noqa: E402

# (番号と名前, 参考写真のファイル, 作者, ライセンス, 昼夜, カメラ位置, 見る先, 焦点距離 mm, 縦横比)
# 角度ごとの追加: roll(度、画像の傾き)、clip(手前を描かない距離 m。カメラが模型の段より下に入るとき)
EXTRA = {
    "02_from_back_north": {"roll": -1.15},
    "01_from_back_south": {"roll": -0.34, "clip": 1.0},
    "04_from_south": {"roll": 1.79, "clip": 4.0},   # 解いたカメラ(高さ 6.6 m)は模型の南スタンドの段より低い。手前 4 m を描かない
}

ITEMS = [
    # 段階 3 で入れた比較(段数・高さ・屋根の奥行の確かめ)。カメラはゴールポスト(高さ 12 m、間隔 5.6 m)が重なるように合わせる
    ("01_from_back_south", "Chichibunomiya3.JPG", "Waka77", "Public domain", "day",
     (-89.9, -71.5, 13.6), (8.6, -4.6, -1.9), 30.0, (3, 2)),   # 南のポスト 6 点、北のポストの根元 2 点、角のフラッグから解いた(平均 1.1 画素)
    ("02_from_back_north", "Chichibunomiya_Rugby1.JPG", "Waka77", "CC0", "day",
     (80.8, -65.7, 11.9), (-1.2, 19.4, -8.8), 27.5, (4, 3)),   # 北のポスト 6 点と南のポスト 4 点から解いた(平均 1.9 画素)
    ("03_back_stand", "秩父宮ラグビー場_(21776716854).jpg", "Tetsuji Sakakibara", "CC BY-SA 2.0", "day",
     (-3.3, 67.2, 12.8), (1.3, -59.3, 1.6), 31.8, (4, 3)),   # 芝のライン 20 点から最小二乗で解いた(平均 1.2 画素)
    ("04_from_south", "Chichibunomiya_Rugby_Stadium2.jpg", "江戸村のとくぞう", "CC BY-SA 4.0", "day",
     (-86.8, -1.1, 6.6), (32.1, -1.3, -9.5), 32.7, (4, 3)),   # 手前と奥のポスト 10 点から解いた(平均 2 画素)
    ("05_behind_north_posts", "Chichibunomiya_Rugby_Stadium-6.jpg", "江戸村のとくぞう", "CC BY-SA 4.0", "day",
     (77.7, 4.6, 4.6), (-60.0, -18.3, 16.4), 46, (3, 2)),
    # 夜のループで足した比較: メインスタンドの前段から北東(北スタンド、得点板、バックスタンドの北の角)。2018 年
    ("06_north_stand", "Chichibunomiya_Rugby_Stadium-w3.jpg", "江戸村のとくぞう", "CC BY-SA 4.0", "day",
     (2.0, 51.9, 7.6), (64.4, -23.7, -12.4), 26.5, (4, 3)),   # 北のポスト 4 点と 22 m ラインから解いた(平均 2.3 画素、傾き 0 に固定)
]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--blend", action="store_true", help="写真と描いた絵を半透明で重ねた画像も out/compare/ に作る(カメラ合わせ用)")
    a = ap.parse_args(argv)
    only = [s for s in a.only.split(",") if s]
    scene = bpy.context.scene
    out_r = os.path.join(config.ROOT, "out", "compare")
    out_d = os.path.join(config.ROOT, "docs", "compare")
    os.makedirs(out_r, exist_ok=True)
    os.makedirs(out_d, exist_ok=True)
    rows = []
    for (name, ref, author, lic, tm, loc, tgt, lens, asp) in ITEMS:
        rows.append((name, ref, author, lic))
        if only and not any(name.startswith(o) for o in only):
            continue
        w = a.width
        h = int(round(w * asp[1] / asp[0] / 2) * 2)
        sky.setup_render(scene, samples=a.samples, res=(w, h))
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 92
        (sky.setup_day if tm == "day" else sky.setup_night)(scene)
        scene.camera = cameras.make(scene, "cmp_" + name, loc, tgt, lens)
        ex = EXTRA.get(name, {})
        if ex.get("roll"):
            from mathutils import Quaternion
            ob = scene.camera
            ob.rotation_euler = (ob.rotation_euler.to_quaternion() @ Quaternion((0, 0, 1), math.radians(ex["roll"]))).to_euler()
        if ex.get("clip"):
            scene.camera.data.clip_start = ex["clip"]
        rp = os.path.join(out_r, name + ".jpg")
        scene.render.filepath = rp
        bpy.ops.render.render(write_still=True)
        refp = os.path.join(config.ROOT, "refs", "commons", ref)
        if os.path.exists(refp):
            H = 640
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", refp, "-i", rp, "-filter_complex",
                            "[0]scale=-2:%d[a];[1]scale=-2:%d[b];[a][b]hstack=inputs=2" % (H, H),
                            "-q:v", "4", os.path.join(out_d, name + ".jpg")], check=False)
            print("[compare] docs/compare/%s.jpg" % name)
            if a.blend:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", refp, "-i", rp, "-filter_complex",
                                "[0]scale=%d:%d[a];[1]format=rgba,colorchannelmixer=aa=0.5[b];[a][b]overlay" % (w, h),
                                "-q:v", "4", os.path.join(out_r, name + "_blend.jpg")], check=False)
                print("[compare] out/compare/%s_blend.jpg" % name)
        else:
            print("[compare] 参考写真がないので並べません:", ref)
    with open(os.path.join(out_d, "README.md"), "w", encoding="utf-8") as f:
        f.write("# 参考写真との比較\n\n")
        f.write("左が参考写真、右がこのモデルを同じ角度から描いたもの。`./run.sh compare` で作り直せる(`--blend` で写真と半透明に重ねた絵も out/compare/ に出る)。\n")
        f.write("カメラの位置と焦点距離は、写っているゴールポスト(高さ 12 m、間隔 5.6 m)の見かけの大きさと位置から計算して置いた。03 は芝のライン 20 点から最小二乗で解き直した(平均 1.2 画素)。01 と 02 は数度のずれが残る。見つかった違いは [../remaining.md](../remaining.md)。\n\n")
        f.write("参考写真はすべて Wikimedia Commons のもので、下の作者とライセンスに従って使っている。\n")
        f.write("CC BY-SA の写真を含む比較画像は、同じ CC BY-SA 4.0 で公開する。写真は大きさだけを変えている。\n\n")
        f.write("| 比較画像 | 参考写真(Wikimedia Commons) | 作者 | ライセンス |\n|---|---|---|---|\n")
        for (name, ref, author, lic) in rows:
            f.write("| [%s.jpg](%s.jpg) | [File:%s](https://commons.wikimedia.org/wiki/File:%s) | %s | %s |\n"
                    % (name, name, ref, ref, author, lic))


main()
