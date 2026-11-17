"""決まった角度のカメラ。名前 → (位置, 見る先, 焦点距離 mm)。センサー幅は 36 mm。"""
import bpy
from mathutils import Vector

# 目盛りつきの空中写真(aerial_grid.py の grid10m.png)の長い辺の画素数と縮尺。重ねるときはここを写真に合わせる
MAP_LONG_SIDE_PX = 1300
MAP_PIXELS_PER_M = 5.0

# 座標: 原点=芝の中心、+X=北北西(北スタンド)、+Y=西(メインスタンド)。高さは芝の面から
VIEWS = {
    # 仕上げの 5 つ(段階 8 で見直す)
    "broadcast": ((0.0, 62.0, 16.5), (0.0, -14.0, 0.0), 22),         # 中継風(メインスタンド後段の中央)
    "behind_goal": ((-84.0, 3.0, 6.5), (30.0, 0.0, 6.0), 26),        # 南のゴール裏から
    "from_seat": ((-35.0, -62.0, 12.5), (45.0, 25.0, 4.0), 22),      # バックスタンドの客席から(写真 064 に近い)
    "aerial": ((-170.0, -150.0, 160.0), (0.0, 5.0, 0.0), 35),        # 空から見下ろす(南東)
    "exterior": ((10.0, 140.0, 1.7), (0.0, 70.0, 12.0), 22),         # 西の正面入場口の外から
    # 確認用
    "top": ((0.0, 0.0, 330.0), (0.0, 0.01, 0.0), 50),
    "pitch_oblique": ((-120.0, 90.0, 70.0), (0.0, 0.0, 0.0), 30),
    "aerial_ne": ((170.0, -140.0, 130.0), (0.0, 0.0, 0.0), 32),
    "aerial_nw": ((150.0, 160.0, 120.0), (0.0, 0.0, 0.0), 32),
    "aerial_wide": ((-340.0, -300.0, 270.0), (-20.0, 10.0, 0.0), 32),   # 南東の高い空から(周りの街まで)
    "aerial_wide_nw": ((330.0, 300.0, 250.0), (0.0, -10.0, 0.0), 32),   # 北西の高い空から(神宮球場の側)
    "main_front": ((0.0, -50.0, 9.0), (0.0, 60.0, 12.0), 20),
    "back_front": ((0.0, 50.0, 8.0), (0.0, -60.0, 7.0), 20),
    "north_front": ((-10.0, 0.0, 6.0), (80.0, 0.0, 6.0), 26),
    "south_front": ((10.0, 0.0, 6.0), (-85.0, 0.0, 8.0), 26),
    "section_west": ((0.0, 20.0, 9.0), (0.0, 120.0, 9.0), 18),       # メインスタンドを横から(断面の確かめ)
    "side_west": ((-110.0, 58.0, 12.0), (0.0, 58.0, 10.0), 30),     # メインスタンドを南の端から(断面の輪郭)
    "side_east": ((-120.0, -58.0, 10.0), (0.0, -58.0, 8.0), 30),    # バックスタンドを南の端から
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def make(scene, name, loc=None, target=None, lens=None):
    if name == "map":
        # 空中写真(refs/map/grid10m.png、1 m = 5 画素)と重ねるための真上からの正射影
        import math
        cam = bpy.data.cameras.new(name)
        cam.type = "ORTHO"
        cam.ortho_scale = MAP_LONG_SIDE_PX / MAP_PIXELS_PER_M
        cam.clip_end = 3000.0
        ob = bpy.data.objects.new("cam_map", cam)
        ob.location = (0, 0, 500)
        ob.rotation_euler = (0, 0, -math.pi / 2)
        scene.collection.objects.link(ob)
        return ob
    if loc is None:
        loc, target, lens = VIEWS[name]
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.1
    cam.clip_end = 30000.0
    ob = bpy.data.objects.new("cam_" + name, cam)
    ob.location = loc
    scene.collection.objects.link(ob)
    look_at(ob, target)
    return ob
