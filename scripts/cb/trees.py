"""木。形の違う原型を数本作り、位置ごとに向き・大きさ・色を変えて並べる(同じメッシュを使い回す)。

前は 1 本ずつ丸い塊 2 つで作っていて、角ばった玉に見えた(本人の指摘と、写真 03・06 の背の高い並木との差)。
原型は高さ 16 m で作り、置くときに縮める。葉は小さな塊(1〜2 m)を樹冠の形の中にたくさん置き、
すき間から枝と奥の暗さが見えるようにする。

  イチョウ(並木。外苑の名物): 細めの円錐に近い卵形
  ケヤキ(林と公園): 下がすぼまり上に広がる扇形
  丸い街路樹(道ぞい)、針葉樹(写真 03 の左に濃い円錐の木)
形と割合は写真からの推定。
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as M

H0 = 16.0       # 原型の高さ


def _foliage():
    """葉の色。木ごとに明るさと色味を少し変え(Object Info の Random)、細かいむらで葉の粒を出す。"""
    m = M._principled("foliage", M.srgb(60, 98, 42), rough=0.85, spec=0.3)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    oi = N.new("ShaderNodeObjectInfo")
    ramp = N.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, M.srgb(44, 78, 34)
    els[1].position, els[1].color = 1.0, M.srgb(92, 120, 52)
    mid = els.new(0.55)
    mid.color = M.srgb(62, 100, 42)
    L.new(oi.outputs["Random"], ramp.inputs["Fac"])
    geo = N.new("ShaderNodeNewGeometry")
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 2.2
    L.new(geo.outputs["Position"], vor.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.72
    mr.inputs["To Max"].default_value = 1.12
    L.new(vor.outputs["Distance"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(ramp.outputs["Color"], mul.inputs["A"])
    L.new(mr.outputs["Result"], mul.inputs["B"])
    L.new(mul.outputs["Result"], b.inputs["Base Color"])
    # 葉の粒の凹凸
    lv = N.new("ShaderNodeTexVoronoi")
    lv.inputs["Scale"].default_value = 7.0
    L.new(geo.outputs["Position"], lv.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.2
    nz.inputs["Detail"].default_value = 4.0
    L.new(geo.outputs["Position"], nz.inputs["Vector"])
    hh = N.new("ShaderNodeMath"); hh.operation = "ADD"
    L.new(lv.outputs["Distance"], hh.inputs[0])
    L.new(nz.outputs["Fac"], hh.inputs[1])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.9
    bp.inputs["Distance"].default_value = 0.25
    L.new(hh.outputs[0], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
    # 日に透ける葉の明るさ(少しだけ)
    try:
        b.inputs["Subsurface Weight"].default_value = 0.0
        b.inputs["Transmission Weight"].default_value = 0.0
    except KeyError:
        pass
    return m


def _bark():
    return M._principled("bark", M.srgb(74, 64, 56), rough=0.9)


# 樹冠の形: (下端, 上端, 最大の半径, 最大になる高さ, 塊の数, 塊の半径) すべて高さ 1 に対する比
SHAPES = {
    "ichou": (0.18, 1.00, 0.21, 0.30, 170, 0.046),
    "keyaki": (0.38, 1.00, 0.44, 0.75, 240, 0.055),
    "round": (0.36, 1.00, 0.36, 0.62, 180, 0.055),
    "conifer": (0.12, 1.00, 0.21, 0.15, 160, 0.042),
}


def _radius_at(shape, t):
    """高さの比 t での樹冠の半径。"""
    z0, z1, rmax, zm, _, _ = shape
    if t <= z0 or t >= z1:
        return 0.0
    if t < zm:
        u = (t - z0) / max(1e-6, zm - z0)
        return rmax * math.sqrt(max(0.0, 1 - (1 - u) ** 2))
    u = (t - zm) / max(1e-6, z1 - zm)
    if shape is SHAPES["ichou"]:
        return rmax * (1 - u) ** 1.1          # 先のとがった円錐(外苑のイチョウ。写真 03 の後ろの細い木)
    return rmax * max(0.0, 1 - u ** 1.6) ** 0.6


def _proto(kind, seed, leaf, bark):
    rnd = random.Random(seed)
    shape = SHAPES[kind]
    z0, z1, rmax, zm, n, cr = shape
    bm = bmesh.new()
    me = bpy.data.meshes.new("tree_%s_%d" % (kind, seed))
    me.materials.append(leaf)
    me.materials.append(bark)

    def add_sphere(c, r, mat, sub=2, jit=0.18):
        g = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r,
                                       matrix=Matrix.Translation(c))
        for v in g["verts"]:
            v.co += (v.co - c).normalized() * r * rnd.uniform(-jit, jit)
        for f in {f for v in g["verts"] for f in v.link_faces}:
            f.material_index = mat
            f.smooth = True

    def add_limb(p0, p1, r0, r1, seg=6):
        d = p1 - p0
        L = d.length
        q = d.to_track_quat("Z", "Y")
        ring0, ring1 = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            o = Vector((math.cos(a), math.sin(a), 0))
            ring0.append(bm.verts.new(p0 + q @ (o * r0)))
            ring1.append(bm.verts.new(p0 + q @ (o * r1 + Vector((0, 0, L)))))
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
            f.material_index = 1
            f.smooth = True

    H = H0
    lean = Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 1.0)).normalized()
    top = lean * (H * (z0 + (z1 - z0) * 0.55))
    add_limb(Vector((0, 0, -0.3)), top, H * 0.022, H * 0.011, seg=8)
    # 葉の塊: 樹冠の中を表面寄りに
    centres = []
    tries = 0
    while len(centres) < n and tries < n * 30:
        tries += 1
        t = rnd.uniform(z0 + 0.02, z1 - 0.02)
        R = _radius_at(shape, t)
        if R <= 0:
            continue
        a = rnd.uniform(0, 2 * math.pi)
        rr = R * rnd.uniform(0.0, 1.0) ** 0.35        # 表面寄り
        c = Vector((rr * math.cos(a), rr * math.sin(a), t)) * 1.0
        c = Vector((c.x * H, c.y * H, c.z * H)) + lean * 0.0
        c.x += lean.x * c.z
        c.y += lean.y * c.z
        centres.append(c)
    for c in centres:
        add_sphere(c, H * cr * rnd.uniform(0.7, 1.35), 0, jit=0.25)
    # 縁の小枝の葉(輪郭を細かくする)
    for c in rnd.sample(centres, len(centres) // 2):
        t = c.z / H
        R = _radius_at(shape, t)
        a = math.atan2(c.y, c.x) + rnd.uniform(-0.4, 0.4)
        e = Vector((math.cos(a) * R * H * rnd.uniform(0.95, 1.12), math.sin(a) * R * H * rnd.uniform(0.95, 1.12),
                    c.z + rnd.uniform(-0.4, 0.6)))
        add_sphere(e, H * cr * rnd.uniform(0.35, 0.6), 0, sub=1, jit=0.3)
    # 太い枝: 幹の途中から外側の塊へ
    for c in rnd.sample(centres, min(7, len(centres))):
        if c.z < H * (z0 + 0.05):
            continue
        p0 = lean * (H * rnd.uniform(z0 * 0.9, z0 + (z1 - z0) * 0.35))
        add_limb(p0, c * 0.85 + p0 * 0.15, H * 0.009, H * 0.004, seg=5)
    bm.to_mesh(me)
    bm.free()
    return me


# 置き場所の種類 → 原型の割合
MIX = {
    "row": {"ichou": 0.75, "keyaki": 0.25},
    "wood": {"ichou": 0.55, "keyaki": 0.25, "conifer": 0.2},
    "aerial": {"ichou": 0.6, "keyaki": 0.25, "conifer": 0.15},
    "lawn": {"keyaki": 0.4, "round": 0.4, "ichou": 0.2},
    "osm": {"round": 0.4, "keyaki": 0.35, "ichou": 0.25},
    "road": {"round": 0.6, "ichou": 0.4},
}
VARIANTS = 3
# 必ず針葉樹にする所: 正面入場口の門の内側の両脇(写真 724・70564・202304011520 の背の高いヒマラヤスギ)
CONIFER_ZONES = [(-30.0, 100.0, 45.0, 131.0)]


def build_trees(pts, heights, c):
    """pts: [(x, y, kind)]、heights: 各木の高さ。原型を作り、同じメッシュを使う物体として並べる。"""
    if "foliage" not in M._cache:
        M._cache["foliage"] = _foliage()
        M._cache["bark"] = _bark()
    leaf, bark = M._cache["foliage"], M._cache["bark"]
    protos = {k: [_proto(k, 100 * i + j, leaf, bark) for j in range(VARIANTS)]
              for i, k in enumerate(SHAPES)}
    rnd = random.Random(2718)
    for idx, ((x, y, kind), h) in enumerate(zip(pts, heights)):
        mix = MIX.get(kind, MIX["osm"])
        if any(x0 <= x <= x1 and y0 <= y <= y1 for (x0, y0, x1, y1) in CONIFER_ZONES):
            mix = {"conifer": 1.0}
        r = rnd.random()
        acc = 0.0
        sel = next(iter(mix))
        for k, w in mix.items():
            acc += w
            if r <= acc:
                sel = k
                break
        me = protos[sel][rnd.randrange(VARIANTS)]
        ob = bpy.data.objects.new("tree_%04d" % idx, me)
        if sel == "ichou":
            h *= rnd.uniform(1.15, 1.4)        # イチョウは周りより頭ひとつ高い(写真 03 で空に突き出る)
        s = h / H0
        w = rnd.uniform(0.88, 1.12)
        ob.scale = (s * w, s * w * rnd.uniform(0.92, 1.08), s)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
        ob.location = (x, y, 0)
        c.objects.link(ob)
    ntri = sum(len(m.polygons) for v in protos.values() for m in v)
    print("[trees] 木 %d 本(原型 %d、原型の面 計 %d)" % (len(pts), sum(len(v) for v in protos.values()), ntri))
