"""マテリアル。名前で取り出す。色はリニア RGB。"""
import bpy

_defs = {}
_cache = {}


def srgb(r, g, b):
    """sRGB(0-255) をリニアに直す。"""
    def f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), 1.0)


def _principled(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0,
                alpha=1.0, transmission=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    m.diffuse_color = color
    return m


def emissive(name, color, day, night, base=None):
    """昼と夜で光の強さを切り替える面(sky.py が切り替える)。"""
    if name in _cache:
        return _cache[name]
    m = _principled(name, base or color, rough=0.3, emit=color, emit_strength=day)
    m["emit_day"] = float(day)
    m["emit_night"] = float(night)
    _cache[name] = m
    return m


def dn_value(nt, day, night, tag=""):
    """昼と夜で値が変わる Value ノードを作り、出力を返す。sky.py がラベル "dn 昼 夜" を見て切り替える。"""
    v = nt.nodes.new("ShaderNodeValue")
    v.label = "dn %g %g %s" % (day, night, tag)
    v.outputs[0].default_value = day
    return v.outputs[0]


def _rainbow(name, base, night=1.1):
    """スクラムスクリーンの斜めの帯。夜は位置ごとに色の変わる虹色に光る(写真から)。"""
    def build():
        m = _principled(name, base, rough=0.5)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(geo.outputs["Position"], sep.inputs[0])
        # 南の弧の中心(-66, 0)から見た角度で色相を決める。正面の 70° ほどで虹を 1 周弱
        dx = N.new("ShaderNodeMath"); dx.operation = "SUBTRACT"
        dx.inputs[0].default_value = -66.0
        L.new(sep.outputs["X"], dx.inputs[1])            # -66 - x (外側が正)
        at = N.new("ShaderNodeMath"); at.operation = "ARCTAN2"
        L.new(sep.outputs["Y"], at.inputs[0]); L.new(dx.outputs[0], at.inputs[1])
        hu = N.new("ShaderNodeMath"); hu.operation = "MULTIPLY_ADD"
        hu.inputs[1].default_value = 0.015 * 57.29578
        hu.inputs[2].default_value = 0.30
        L.new(at.outputs[0], hu.inputs[0])
        # 高さでも少し色をずらす(帯の中で色がにじんで見える)
        hz_ = N.new("ShaderNodeMath"); hz_.operation = "MULTIPLY_ADD"
        hz_.inputs[1].default_value = 0.006
        L.new(sep.outputs["Z"], hz_.inputs[0]); L.new(hu.outputs[0], hz_.inputs[2])
        fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"
        L.new(hz_.outputs[0], fr.inputs[0])
        cc = N.new("ShaderNodeCombineColor"); cc.mode = "HSV"
        cc.inputs[1].default_value = 1.0
        cc.inputs[2].default_value = 1.0
        L.new(fr.outputs[0], cc.inputs[0])
        L.new(cc.outputs[0], b.inputs["Emission Color"])
        L.new(dn_value(nt, 0.0, night, "rainbow"), b.inputs["Emission Strength"])
        return m
    return build


def _house_wall(name, color, rough=0.9, metal=0.0, spec=0.5, fl=3.0, ww=2.6, wx=(0.25, 0.75), wz=(0.35, 0.78),
                shop=False, dirt=0.12):
    """家やマンションの壁。窓の格子を描き、夜は 3 割ほどの窓に明かりがともる。
    rough を小さくするとガラスの外壁(空を映す)。fl = 階の高さ、ww = 窓の間隔、wx・wz = 窓の幅と高さの範囲(比)。
    wx が (0, 1) なら横に続く窓(事務所の連続窓)。shop = 1 階を暗いガラスの店先に。dirt = 雨だれのむら。"""
    def build():
        m = _principled(name, color, rough=rough, metal=metal, spec=spec)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(geo.outputs["Position"], sep.inputs[0])

        def mth(op, a, v=None, bs=None):
            n = N.new("ShaderNodeMath"); n.operation = op
            L.new(a, n.inputs[0])
            if bs is not None:
                L.new(bs, n.inputs[1])
            elif v is not None:
                n.inputs[1].default_value = v
            return n.outputs[0]
        h = mth("DIVIDE", mth("ADD", sep.outputs["X"], bs=sep.outputs["Y"]), ww)
        zz = mth("DIVIDE", sep.outputs["Z"], fl)
        fh, fz = mth("FRACT", h), mth("FRACT", zz)
        inside = mth("MULTIPLY", mth("MULTIPLY", mth("GREATER_THAN", fh, wx[0]), bs=mth("LESS_THAN", fh, wx[1])),
                     bs=mth("MULTIPLY", mth("GREATER_THAN", fz, wz[0]), bs=mth("LESS_THAN", fz, wz[1])))
        if wx[1] - wx[0] >= 0.99:
            # 連続窓の縦の桟(細い線)
            mu = mth("FRACT", mth("MULTIPLY", h, 2.0))
            inside = mth("MULTIPLY", inside, bs=mth("GREATER_THAN", mu, 0.06))
        z0 = (fl + 0.8) if shop else 0.8
        win = mth("MULTIPLY", inside, bs=mth("GREATER_THAN", sep.outputs["Z"], z0))
        if shop:
            # 1 階の店先: 暗いガラスと、柱の間隔ごとの白い枠
            g = mth("LESS_THAN", sep.outputs["Z"], fl * 0.95)
            g = mth("MULTIPLY", g, bs=mth("GREATER_THAN", sep.outputs["Z"], 0.25))
            g = mth("MULTIPLY", g, bs=mth("GREATER_THAN", mth("FRACT", mth("DIVIDE", h, 2.0)), 0.06))
            win = mth("MAXIMUM", win, bs=g)
        comb = N.new("ShaderNodeCombineXYZ")
        L.new(mth("FLOOR", h), comb.inputs[0]); L.new(mth("FLOOR", zz), comb.inputs[1])
        L.new(mth("FLOOR", mth("DIVIDE", mth("SUBTRACT", sep.outputs["X"], bs=sep.outputs["Y"]), 7.0)), comb.inputs[2])
        wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
        L.new(comb.outputs[0], wn.inputs["Vector"])
        lit = mth("MULTIPLY", win, bs=mth("LESS_THAN", wn.outputs["Value"], 0.32))
        # 昼: 窓は暗いガラスに
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
        mx.inputs["B"].default_value = (0.05, 0.06, 0.07, 1)
        if dirt:
            # 雨だれ: 縦に伸ばしたむらで壁の色を少し暗く(上ほど強い汚れは省略)
            sc = N.new("ShaderNodeMapping")
            sc.inputs["Scale"].default_value = (0.35, 0.35, 0.04)
            L.new(geo.outputs["Position"], sc.inputs["Vector"])
            dn = N.new("ShaderNodeTexNoise")
            dn.inputs["Scale"].default_value = 3.0
            dn.inputs["Detail"].default_value = 6.0
            L.new(sc.outputs["Vector"], dn.inputs["Vector"])
            dm = N.new("ShaderNodeMapRange")
            dm.inputs["To Min"].default_value = 1.0 - dirt
            dm.inputs["To Max"].default_value = 1.0 + dirt * 0.4
            L.new(dn.outputs["Fac"], dm.inputs["Value"])
            wc0 = N.new("ShaderNodeMix"); wc0.data_type = "RGBA"; wc0.blend_type = "MULTIPLY"
            wc0.inputs["Factor"].default_value = 1.0
            wc0.inputs["A"].default_value = color
            L.new(dm.outputs["Result"], wc0.inputs["B"])
            L.new(wc0.outputs["Result"], mx.inputs["A"])
        else:
            mx.inputs["A"].default_value = color
        L.new(mth("MULTIPLY", win, 0.75), mx.inputs["Factor"])
        L.new(mx.outputs["Result"], b.inputs["Base Color"])
        # 夜: 暖かい色と白っぽい色の明かり
        wc = N.new("ShaderNodeMix"); wc.data_type = "RGBA"
        wc.inputs["A"].default_value = (1.0, 0.72, 0.42, 1)
        wc.inputs["B"].default_value = (0.92, 0.95, 1.0, 1)
        L.new(mth("GREATER_THAN", wn.outputs["Value"], 0.2), wc.inputs["Factor"])
        ec = N.new("ShaderNodeMix"); ec.data_type = "RGBA"
        ec.inputs["A"].default_value = (0, 0, 0, 1)
        L.new(lit, ec.inputs["Factor"]); L.new(wc.outputs["Result"], ec.inputs["B"])
        L.new(ec.outputs["Result"], b.inputs["Emission Color"])
        L.new(dn_value(nt, 0.0, 3.0, "windows"), b.inputs["Emission Strength"])
        return m
    return build


HAZE_START = 220.0      # ここまでは霞まない(スタジアムのまわり)
HAZE_SCALE = 2600.0     # これだけ離れると 6 割ほど霞む


def add_haze(m):
    """遠くの物ほど空の色に溶かす(空気遠近)。マテリアルの出力の手前に混ぜる。"""
    if not m.use_nodes or m.get("hazed"):
        return
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    out = next((n for n in N if n.type == "OUTPUT_MATERIAL"), None)
    if out is None or not out.inputs["Surface"].links:
        return
    src = out.inputs["Surface"].links[0].from_socket
    cam = N.new("ShaderNodeCameraData")
    d = N.new("ShaderNodeMath"); d.operation = "SUBTRACT"
    L.new(cam.outputs["View Distance"], d.inputs[0]); d.inputs[1].default_value = HAZE_START
    d2 = N.new("ShaderNodeMath"); d2.operation = "MAXIMUM"
    L.new(d.outputs[0], d2.inputs[0]); d2.inputs[1].default_value = 0.0
    d3 = N.new("ShaderNodeMath"); d3.operation = "DIVIDE"
    L.new(d2.outputs[0], d3.inputs[0]); d3.inputs[1].default_value = -HAZE_SCALE
    e = N.new("ShaderNodeMath"); e.operation = "EXPONENT"
    L.new(d3.outputs[0], e.inputs[0])
    f = N.new("ShaderNodeMath"); f.operation = "SUBTRACT"
    f.inputs[0].default_value = 1.0; L.new(e.outputs[0], f.inputs[1])
    f2 = N.new("ShaderNodeMath"); f2.operation = "MULTIPLY"
    L.new(f.outputs[0], f2.inputs[0])
    L.new(dn_value(nt, 0.92, 0.85, "haze_max"), f2.inputs[1])
    col = N.new("ShaderNodeMix"); col.data_type = "RGBA"
    col.inputs["A"].default_value = HAZE_DAY
    col.inputs["B"].default_value = HAZE_NIGHT
    L.new(dn_value(nt, 0.0, 1.0, "haze_col"), col.inputs["Factor"])
    em = N.new("ShaderNodeEmission")
    L.new(col.outputs["Result"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    ms = N.new("ShaderNodeMixShader")
    L.new(f2.outputs[0], ms.inputs[0])
    L.new(src, ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs["Surface"])
    m["hazed"] = 1


import os as _os
HAZE_DAY = tuple(float(v) for v in _os.environ.get("HZ_HAZE", "0.50,0.58,0.70").split(",")) + (1.0,)
HAZE_NIGHT = (0.018, 0.028, 0.062, 1.0)


def haze_all():
    for m in list(_cache.values()):
        add_haze(m)


def define(name, **kw):
    _defs[name] = kw


def get(name):
    if name in _cache:
        return _cache[name]
    if name in _builders:
        m = _builders[name]()
    else:
        m = _principled(name, **_defs[name])
    _cache[name] = m
    return m


def clear():
    _cache.clear()


# ---- 手続きで作るもの ----

def _grass():
    m = bpy.data.materials.new("grass")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs[0])

    def stripe(axis_out, width, offset):
        a = N.new("ShaderNodeMath"); a.operation = "ADD"
        a.inputs[1].default_value = 1000.0 + offset
        L.new(axis_out, a.inputs[0])
        d = N.new("ShaderNodeMath"); d.operation = "DIVIDE"
        d.inputs[1].default_value = width
        L.new(a.outputs[0], d.inputs[0])
        fl = N.new("ShaderNodeMath"); fl.operation = "FLOOR"
        L.new(d.outputs[0], fl.inputs[0])
        mo = N.new("ShaderNodeMath"); mo.operation = "MODULO"
        mo.inputs[1].default_value = 2.0
        L.new(fl.outputs[0], mo.inputs[0])
        return mo.outputs[0]

    from . import config
    t = config.load()["turf"]
    # ゴールラインに平行な帯(幅 5 m)。22 m ラインなどと境目が合うよう 0 を境にする
    s_cross = stripe(sep.outputs["X"], t["stripe_width_cross"], 0.0)
    s_long = stripe(sep.outputs["Y"], t["stripe_width_long"], 0.0)
    mix = N.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"
    mix.inputs[1].default_value = 0.85
    L.new(s_cross, mix.inputs[0])
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = 0.15
    L.new(s_long, m2.inputs[0])
    L.new(m2.outputs[0], mix.inputs[2])

    # むら
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.12
    noise.inputs["Detail"].default_value = 6.0
    L.new(geo.outputs["Position"], noise.inputs["Vector"])
    fine = N.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 18.0
    fine.inputs["Detail"].default_value = 3.0
    L.new(geo.outputs["Position"], fine.inputs["Vector"])

    ramp = N.new("ShaderNodeMix"); ramp.data_type = "RGBA"
    ramp.inputs["A"].default_value = (0.030, 0.088, 0.008, 1)
    ramp.inputs["B"].default_value = (0.042, 0.118, 0.011, 1)
    L.new(mix.outputs[0], ramp.inputs["Factor"])
    var = N.new("ShaderNodeMix"); var.data_type = "RGBA"; var.blend_type = "MULTIPLY"
    var.inputs["Factor"].default_value = 0.35
    L.new(ramp.outputs["Result"], var.inputs["A"])
    L.new(noise.outputs["Color"], var.inputs["B"])
    cr = N.new("ShaderNodeMix"); cr.data_type = "RGBA"; cr.blend_type = "OVERLAY"
    cr.inputs["Factor"].default_value = 0.25
    L.new(var.outputs["Result"], cr.inputs["A"])
    L.new(fine.outputs["Color"], cr.inputs["B"])
    L.new(cr.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.04
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.03
    L.new(fine.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _noisy(name, color, rough, scale=1.5, amount=0.25, bump=0.0, metal=0.0):
    """色にゆるいむらを入れたマテリアル(コンクリートや舗装)。"""
    def build():
        m = _principled(name, color, rough=rough, metal=metal)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        noise = N.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.65
        L.new(geo.outputs["Position"], noise.inputs["Vector"])
        mp = N.new("ShaderNodeMapRange")
        mp.inputs["To Min"].default_value = 1.0 - amount
        mp.inputs["To Max"].default_value = 1.0 + amount
        L.new(noise.outputs["Fac"], mp.inputs["Value"])
        mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mul.inputs["A"].default_value = color
        L.new(mp.outputs["Result"], mul.inputs["B"])
        L.new(mul.outputs["Result"], b.inputs["Base Color"])
        if bump:
            bp = N.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            bp.inputs["Distance"].default_value = 0.01
            n2 = N.new("ShaderNodeTexNoise")
            n2.inputs["Scale"].default_value = 60.0
            L.new(geo.outputs["Position"], n2.inputs["Vector"])
            L.new(n2.outputs["Fac"], bp.inputs["Height"])
            L.new(bp.outputs["Normal"], b.inputs["Normal"])
        return m
    return build


def _concrete(name, color, rough=0.85, bump=0.15, patch=0.14, streak=0.16):
    """古いコンクリート(1947 年開場、何度も直した躯体)。大きなまだら、細かいむら、縦の雨だれの 3 つを重ねる。"""
    def build():
        m = _principled(name, color, rough=rough)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")

        def noise(scale, vec=None, detail=6.0):
            n = N.new("ShaderNodeTexNoise")
            n.inputs["Scale"].default_value = scale
            n.inputs["Detail"].default_value = detail
            n.inputs["Roughness"].default_value = 0.6
            L.new(vec if vec is not None else geo.outputs["Position"], n.inputs["Vector"])
            return n.outputs["Fac"]

        def rng(v, lo, hi, f0=0.3, f1=0.7):
            r = N.new("ShaderNodeMapRange")
            r.inputs["From Min"].default_value = f0
            r.inputs["From Max"].default_value = f1
            r.inputs["To Min"].default_value = lo
            r.inputs["To Max"].default_value = hi
            L.new(v, r.inputs["Value"])
            return r.outputs["Result"]

        def mul(a, bb):
            n = N.new("ShaderNodeMath"); n.operation = "MULTIPLY"
            L.new(a, n.inputs[0]); L.new(bb, n.inputs[1])
            return n.outputs[0]
        big = rng(noise(0.06), 1.0 - patch, 1.0 + patch * 0.5)
        mid = rng(noise(0.9), 0.93, 1.05)
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.6, 0.6, 0.05)
        L.new(geo.outputs["Position"], mp.inputs["Vector"])
        st = rng(noise(4.0, mp.outputs["Vector"], 4.0), 1.0 - streak, 1.0, 0.45, 0.75)
        f = mul(mul(big, mid), st)
        c = N.new("ShaderNodeMix"); c.data_type = "RGBA"; c.blend_type = "MULTIPLY"
        c.inputs["Factor"].default_value = 1.0
        c.inputs["A"].default_value = color
        L.new(f, c.inputs["B"])
        L.new(c.outputs["Result"], b.inputs["Base Color"])
        rr = rng(noise(0.9), rough - 0.08, rough + 0.08)
        L.new(rr, b.inputs["Roughness"])
        bp = N.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.01
        L.new(noise(40.0), bp.inputs["Height"])
        L.new(bp.outputs["Normal"], b.inputs["Normal"])
        return m
    return build


def _seat(name, color):
    """座席。1 脚ごとに色を少し変える(日焼けと取り替えの差。Object Info の Random は点に並べた 1 脚ごとに変わる)。"""
    def build():
        m = _principled(name, color, rough=0.5, spec=0.35)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        oi = N.new("ShaderNodeObjectInfo")
        r = N.new("ShaderNodeMapRange")
        r.inputs["To Min"].default_value = 0.86
        r.inputs["To Max"].default_value = 1.06
        L.new(oi.outputs["Random"], r.inputs["Value"])
        c = N.new("ShaderNodeMix"); c.data_type = "RGBA"; c.blend_type = "MULTIPLY"
        c.inputs["Factor"].default_value = 1.0
        c.inputs["A"].default_value = color
        L.new(r.outputs["Result"], c.inputs["B"])
        L.new(c.outputs["Result"], b.inputs["Base Color"])
        return m
    return build


def _scrum_tiles():
    """スクラムスクリーンの下地。菱形のタイルを灰色の濃淡とガラスで塗り分ける(面は X 一定)。"""
    m = _principled("scrum_tiles", (0.4, 0.4, 0.4, 1), rough=0.45)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs[0])

    def math(op, a, bval=None, b_sock=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        L.new(a, n.inputs[0])
        if b_sock is not None:
            L.new(b_sock, n.inputs[1])
        elif bval is not None:
            n.inputs[1].default_value = bval
        return n.outputs[0]
    yy = math("DIVIDE", sep.outputs["Y"], 0.8)
    zz = math("DIVIDE", sep.outputs["Z"], 1.6)
    a = math("ADD", yy, b_sock=zz)
    bb = math("SUBTRACT", yy, b_sock=zz)
    fa, fb = math("FLOOR", a), math("FLOOR", bb)
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(fa, comb.inputs[0]); L.new(fb, comb.inputs[1])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "2D"
    L.new(comb.outputs[0], wn.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0; els[0].color = (0.035, 0.045, 0.055, 1)
    els[1].position = 0.26; els[1].color = srgb(96, 102, 110)
    for pos, col in ((0.5, srgb(132, 136, 140)), (0.74, srgb(166, 168, 170)), (0.92, srgb(200, 200, 198))):
        e = els.new(pos); e.color = col
    # 白い乱数に高さを混ぜて、下ほど暗いガラス・上ほど明るいタイルが規則的に並ぶようにする
    zn = math("DIVIDE", sep.outputs["Z"], 23.6)
    mix_v = N.new("ShaderNodeMix"); mix_v.data_type = "FLOAT"
    mix_v.inputs["Factor"].default_value = 0.5
    L.new(wn.outputs["Value"], mix_v.inputs["A"])
    L.new(zn, mix_v.inputs["B"])
    # 階の高さ(4.5〜8.5 m、11〜14 m)はガラスの帯
    b1 = math("MULTIPLY", math("GREATER_THAN", sep.outputs["Z"], 4.5), b_sock=math("LESS_THAN", sep.outputs["Z"], 8.5))
    b2 = math("MULTIPLY", math("GREATER_THAN", sep.outputs["Z"], 11.0), b_sock=math("LESS_THAN", sep.outputs["Z"], 14.0))
    band = math("MULTIPLY", math("ADD", b1, b_sock=b2), 0.22)
    vv = math("SUBTRACT", mix_v.outputs["Result"], b_sock=band)
    L.new(vv, ramp.inputs["Fac"])
    # 夜はガラスのタイルに中の明かりがともる
    glass = math("MULTIPLY", math("LESS_THAN", vv, 0.26), b_sock=math("ADD", b1, b_sock=b2))
    em = N.new("ShaderNodeMix"); em.data_type = "RGBA"
    em.inputs["A"].default_value = (0, 0, 0, 1)
    em.inputs["B"].default_value = (0.95, 0.92, 0.85, 1)
    L.new(glass, em.inputs["Factor"])
    L.new(em.outputs["Result"], b.inputs["Emission Color"])
    L.new(dn_value(nt, 0.0, 1.3, "tiles"), b.inputs["Emission Strength"])
    # 目地
    fra, frb = math("FRACT", a), math("FRACT", bb)
    mn = math("MINIMUM", fra, b_sock=frb)
    joint = math("GREATER_THAN", mn, 0.035)
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(ramp.outputs["Color"], mul.inputs["A"])
    jc = N.new("ShaderNodeMapRange")
    jc.inputs["To Min"].default_value = 0.45
    L.new(joint, jc.inputs["Value"])
    L.new(jc.outputs["Result"], mul.inputs["B"])
    L.new(mul.outputs["Result"], b.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange")
    rr.inputs["From Max"].default_value = 0.26
    rr.inputs["To Min"].default_value = 0.08
    rr.inputs["To Max"].default_value = 0.5
    L.new(vv, rr.inputs["Value"])
    L.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def _brick_paving():
    m = _principled("paving_brick", srgb(140, 92, 76), rough=0.9)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    br = N.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = srgb(146, 96, 78)
    br.inputs["Color2"].default_value = srgb(126, 82, 70)
    br.inputs["Mortar"].default_value = srgb(96, 78, 70)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.42
    br.inputs["Row Height"].default_value = 0.21
    L.new(geo.outputs["Position"], br.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.08
    L.new(geo.outputs["Position"], noise.inputs["Vector"])
    mp = N.new("ShaderNodeMapRange")
    mp.inputs["To Min"].default_value = 0.8
    mp.inputs["To Max"].default_value = 1.15
    L.new(noise.outputs["Fac"], mp.inputs["Value"])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(br.outputs["Color"], mul.inputs["A"])
    L.new(mp.outputs["Result"], mul.inputs["B"])
    L.new(mul.outputs["Result"], b.inputs["Base Color"])
    return m


_builders = {
    "scrum_tiles": _scrum_tiles,
    "scrum_dark": _rainbow("scrum_dark", srgb(62, 70, 84)),
    "scrum_light": _rainbow("scrum_light", srgb(196, 199, 202), night=0.0),
    "house_a": _house_wall("house_a", srgb(168, 162, 150)),
    "house_b": _house_wall("house_b", srgb(146, 144, 138)),
    "house_c": _house_wall("house_c", srgb(182, 176, 164)),
    "apart_a": _house_wall("apart_a", srgb(198, 194, 184), fl=2.9, ww=3.4, wx=(0.12, 0.88), wz=(0.12, 0.80)),
    "apart_b": _house_wall("apart_b", srgb(156, 150, 140), fl=2.9, ww=3.0, wx=(0.2, 0.8), wz=(0.3, 0.8), shop=True),
    "apart_c": _house_wall("apart_c", srgb(222, 216, 204), fl=2.9, ww=3.6, wx=(0.1, 0.9), wz=(0.15, 0.78)),
    # 秩父宮のまわり(北青山)の事務所ビル。窓の格子は家と同じ仕組み
    "office_a": _house_wall("office_a", srgb(188, 190, 192), fl=3.8, wx=(0.0, 1.0), wz=(0.30, 0.82), shop=True),
    "office_b": _house_wall("office_b", srgb(120, 132, 146), fl=3.8, ww=1.8, wx=(0.18, 0.82), wz=(0.25, 0.85), shop=True),
    "office_c": _house_wall("office_c", srgb(200, 190, 172), fl=3.6, ww=3.2, wx=(0.2, 0.8), wz=(0.3, 0.8), shop=True),
    "office_e": _house_wall("office_e", srgb(214, 212, 206), fl=3.8, wx=(0.0, 1.0), wz=(0.42, 0.85), shop=True),
    "office_f": _house_wall("office_f", srgb(150, 140, 128), fl=3.6, ww=1.5, wx=(0.22, 0.78), wz=(0.2, 0.86), shop=True),
    "office_d": _house_wall("office_d", srgb(92, 84, 80)),
    # 高層のガラスの外壁(写真 05 の青山OM-SQUARE、写真 02 の左の塔): 暗い青緑のガラス、空を映す
    # 階ごとの白っぽい帯(床の位置)と、そのあいだの暗いガラス。縦の桟は 1.3 m おき
    "office_glass": _house_wall("office_glass", srgb(150, 162, 170), rough=0.12, metal=0.35, spec=0.8,
                                fl=4.0, ww=2.6, wx=(0.0, 1.0), wz=(0.0, 0.78), dirt=0.0),
    "office_glass2": _house_wall("office_glass2", srgb(168, 170, 172), rough=0.18, metal=0.25, spec=0.7,
                                 fl=4.0, ww=3.0, wx=(0.0, 1.0), wz=(0.0, 0.72), dirt=0.0),
    "roof_flat_a": _noisy("roof_flat_a", srgb(150, 150, 148), 0.9, scale=0.3, amount=0.15),
    "roof_flat_b": _noisy("roof_flat_b", srgb(118, 122, 124), 0.9, scale=0.3, amount=0.15),
    "court": _noisy("court", srgb(150, 158, 128), 0.85, scale=0.5, amount=0.08),   # 砂入り人工芝(空中写真のコートの中は (168,174,158)〜(182,174,162) の色みの薄い灰緑・灰ベージュ)
    "paving_light": _noisy("paving_light", srgb(178, 174, 166), 0.9, scale=0.6, amount=0.10),
    "brick_wall": _noisy("brick_wall", srgb(150, 86, 66), 0.9, scale=0.8, amount=0.15),
    "ground_far": _noisy("ground_far", srgb(104, 110, 102), 0.95, scale=0.004, amount=0.2),
    "turf2": _noisy("turf2", srgb(40, 96, 50), 0.9, scale=0.2, amount=0.12),
    "hockey": _noisy("hockey", srgb(96, 160, 150), 0.85, scale=0.2, amount=0.06),
    "asphalt_dark": _noisy("asphalt_dark", srgb(66, 66, 70), 0.95, scale=0.5, amount=0.15),
    "leaf_a": _noisy("leaf_a", srgb(52, 92, 40), 0.9, scale=1.5, amount=0.35),
    "leaf_b": _noisy("leaf_b", srgb(70, 108, 46), 0.9, scale=1.5, amount=0.35),
    "mountain": _noisy("mountain", srgb(44, 64, 66), 1.0, scale=0.004, amount=0.15),
    "grass": _grass,
    "concrete": _concrete("concrete", srgb(150, 148, 142)),
    "concrete_dark": _concrete("concrete_dark", srgb(72, 72, 74), rough=0.9),
    "concrete_light": _concrete("concrete_light", srgb(180, 178, 172), rough=0.8, patch=0.12, streak=0.12),
    "seat_blue": _seat("seat_blue", srgb(70, 150, 212)),
    "seat_yellow": _seat("seat_yellow", srgb(206, 186, 104)),
    "asphalt": _noisy("asphalt", srgb(92, 92, 94), 0.95, scale=0.5, amount=0.15, bump=0.2),
    "paving_brick": _brick_paving,
    "paving_brick_plain": _noisy("paving_brick", srgb(140, 92, 76), 0.9, scale=0.6, amount=0.12, bump=0.15),
    "paving_grey": _noisy("paving_grey", srgb(170, 168, 162), 0.9, scale=0.6, amount=0.10, bump=0.15),
    "apron": _noisy("apron", srgb(18, 86, 40), 0.9, scale=2.0, amount=0.10, bump=0.3),
    "lawn": _noisy("lawn", srgb(74, 110, 52), 0.95, scale=0.3, amount=0.25, bump=0.3),
    "dirt": _noisy("dirt", srgb(170, 150, 118), 0.95, scale=0.3, amount=0.15),
}

# ---- 単色のもの ----
define("line_white", color=srgb(238, 240, 236), rough=0.8)
define("white_paint", color=srgb(236, 236, 232), rough=0.45)
define("white_steel", color=srgb(228, 230, 230), rough=0.4, metal=0.0)
define("grey_steel", color=srgb(140, 144, 148), rough=0.45, metal=0.6)
define("dark_steel", color=srgb(38, 40, 44), rough=0.5, metal=0.3)
define("black", color=srgb(16, 16, 18), rough=0.6)
define("pad_white", color=srgb(240, 240, 240), rough=0.55)
define("pad_red", color=srgb(196, 30, 36), rough=0.55)
define("flag_red", color=srgb(214, 36, 40), rough=0.7)
define("seat_red", color=srgb(200, 22, 16), rough=0.6, spec=0.3)
# 秩父宮: 水色寄りの青と、からし色の黄(写真の日なたの青は sRGB で約 (119,175,219))
define("vom_blue", color=srgb(118, 168, 204), rough=0.6)     # 写真 023・025 の箱の空色(座席より少し灰色)
define("vom_inner", color=srgb(52, 78, 104), rough=0.8)      # 箱の内側の天井(影の濃い青)
define("vom_yellow", color=srgb(222, 204, 128), rough=0.7)
define("vom_red", color=srgb(196, 44, 40), rough=0.6)
define("jingu_seats", color=srgb(46, 92, 168), rough=0.6)
define("facade_beige", color=srgb(200, 196, 182), rough=0.8)    # メインの裏の明るい板と帯の四角(写真 413・048・005)
define("facade_grey", color=srgb(140, 140, 130), rough=0.85)    # メインの裏の帯と部屋の階の外壁(写真 413 の緑がかった灰色)
define("concourse_dark", color=srgb(46, 48, 50), rough=0.9)     # スタンドの下の暗い吹き抜け
define("gate_grey", color=srgb(104, 98, 92), rough=0.7)          # 正面入場口の角柱(写真 031・724 の焦げ茶がかった灰色)
define("gate_red", color=srgb(196, 72, 44), rough=0.6)          # 角柱の外の角の赤い縦の線(写真 724・45)
define("gate_board", color=srgb(84, 70, 60), rough=0.75)        # 門の上の看板の枠の板(行事のない日の焦げ茶。写真 724)
define("gate_bronze", color=srgb(92, 84, 72), rough=0.6, metal=0.3)  # 門の梁(施設名の板)
define("gate_letters", color=srgb(176, 168, 150), rough=0.5, metal=0.4)
define("nat_seats", color=srgb(112, 118, 96), rough=0.7)        # 国立競技場の客席(白・黄緑・深緑・茶のまだら。遠目の平均)
define("wood_louver", color=srgb(146, 108, 72), rough=0.8)      # 国立競技場の外の軒(木のルーバー)
define("track_red", color=srgb(168, 74, 56), rough=0.85)        # 陸上のトラック
define("water", color=srgb(48, 88, 112), rough=0.08, spec=0.6)
define("seat_grey", color=srgb(150, 152, 156), rough=0.42)
define("glass", color=srgb(150, 175, 185), rough=0.06, metal=0.0, transmission=0.0, alpha=1.0, spec=1.0, coat=1.0)
define("glass_dark", color=srgb(34, 44, 52), rough=0.05, spec=1.0, coat=1.0)
define("poly_clear", color=srgb(225, 235, 240), rough=0.15, alpha=0.35)
define("bench_blue", color=srgb(30, 60, 130), rough=0.5)
define("fence_mesh", color=srgb(96, 112, 104), rough=0.6, metal=0.3, alpha=0.38)   # 網の柵(写真 018・025。目の細かい金網を半透明で)
define("aluminium", color=srgb(190, 192, 194), rough=0.35, metal=0.9)
define("roof_sheet", color=srgb(196, 198, 196), rough=0.55, metal=0.2)
define("roof_under", color=srgb(214, 214, 210), rough=0.6)
define("screen_frame", color=srgb(52, 56, 60), rough=0.5)
define("lamp_off", color=srgb(210, 212, 205), rough=0.3)
define("tower_pole", color=srgb(40, 36, 34), rough=0.55, metal=0.2)
define("flag_a", color=srgb(240, 240, 240), rough=0.7)
define("flag_b", color=srgb(30, 70, 160), rough=0.7)
define("flag_c", color=srgb(150, 30, 50), rough=0.7)
define("flag_d", color=srgb(40, 130, 70), rough=0.7)
define("sign_white", color=srgb(240, 240, 236), rough=0.5)
define("sign_blue", color=srgb(20, 90, 170), rough=0.5)
define("sign_green", color=srgb(30, 120, 80), rough=0.5)
define("sign_yellow", color=srgb(240, 200, 40), rough=0.5)
define("sign_red", color=srgb(200, 40, 40), rough=0.5)
define("sign_navy", color=srgb(20, 30, 70), rough=0.5)
define("text_dark", color=srgb(20, 22, 30), rough=0.6)
define("text_white", color=srgb(245, 245, 245), rough=0.6)
define("text_red", color=srgb(200, 30, 36), rough=0.6)
define("trunk", color=srgb(80, 62, 48), rough=0.9)
define("roof_a", color=srgb(62, 66, 74), rough=0.8)
define("roof_membrane", color=srgb(232, 234, 232), rough=0.45)
define("roof_gear", color=srgb(176, 178, 176), rough=0.5, metal=0.3)
define("roof_b", color=srgb(58, 76, 104), rough=0.8)
define("roof_c", color=srgb(98, 80, 72), rough=0.8)
define("aisle_dark", color=srgb(46, 46, 50), rough=0.9)
define("factory_roof", color=srgb(120, 132, 140), rough=0.5, metal=0.4)
define("factory_wall", color=srgb(176, 178, 176), rough=0.8)
define("rail", color=srgb(120, 110, 100), rough=0.4, metal=0.8)
define("ballast", color=srgb(110, 104, 96), rough=1.0)
define("train_body", color=srgb(220, 222, 224), rough=0.4)
