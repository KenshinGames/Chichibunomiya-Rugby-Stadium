"""スタジアムを最初から作って build/chichibu.blend に保存する。

  blender -b --factory-startup -P scripts/build.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from cb import config, materials, util  # noqa: E402

# ない部品は飛ばす。段階 4 以降で roof(骨組み)、seats、details、screen、lights、exterior、signage を足す
STAGES = ["pitch", "stands", "roof", "seats", "details", "screen", "lights", "exterior", "signage"]


def main():
    t0 = time.time()
    util.reset_scene()
    materials.clear()
    import importlib
    for name in STAGES:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb", name + ".py")
        if not os.path.exists(path):
            continue
        mod = importlib.import_module("cb." + name)
        t = time.time()
        mod.build()
        print("[build] %-9s %.1f 秒" % (name, time.time() - t))
    materials.haze_all()
    out = os.path.join(config.ROOT, "build")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "chichibu.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    nobj = len(bpy.data.objects)
    ntri = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    print("[build] 保存 %s (オブジェクト %d、面 %d、%.1f 秒)" % (path, nobj, ntri, time.time() - t0))


main()
