# Gera os assets low-poly (estilo PS2) do Jet Ski Curitiba, com cores por vértice
# na paleta da família Folha, e exporta tudo num único assets.glb.
# Uso: blender -b -P blender/assets_ps2.py -- <pasta_saida>
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.dirname(__file__)
bpy.ops.wm.read_factory_settings(use_empty=True)

# paleta (sRGB)
LIMA, FOLHA, FOLHA_ESC, TINTA = 0xb5cc2e, 0x5a9a4a, 0x3f8a46, 0x1e5e34
LARANJA, VERMELHO, AMARELO, LILAS, JEANS = 0xf39a2b, 0xd93a3a, 0xf2c230, 0xa05ab8, 0x3a6fd9
BRANCO, CREME, CINZA, CINZA_ESC, PRETO = 0xf4f4ec, 0xe9e4cf, 0x9a9c92, 0x6b6d66, 0x2a2f2c
CAPI, CAPI_ESC, CAPI_FOCINHO, MADEIRA, VIDRO = 0x8a5a2b, 0x6e4520, 0x3a2618, 0x6b4a2f, 0x1e3a2e


def hexc(h):
    return ((h >> 16 & 255) / 255, (h >> 8 & 255) / 255, (h & 255) / 255, 1.0)


def paint(o, col):
    me = o.data
    ca = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    c = hexc(col)
    for d in ca.data:
        d.color_srgb = c
    return o


def finish(o, col, smooth=False):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for p in o.data.polygons:
        p.use_smooth = smooth
    return paint(o, col)


def prim(kind, col, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=False, bevel=0, **kw):
    getattr(bpy.ops.mesh, 'primitive_' + kind + '_add')(**kw)
    o = bpy.context.active_object
    o.location, o.rotation_euler, o.scale = loc, rot, scale
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        m = o.modifiers.new('b', 'BEVEL'); m.width = bevel; m.segments = 1
        bpy.ops.object.modifier_apply(modifier='b')
    return finish(o, col, smooth)


def box(col, loc, size, rot=(0, 0, 0), bevel=0):
    return prim('cube', col, loc, rot, (size[0] / 2, size[1] / 2, size[2] / 2), bevel=bevel)


def cyl(col, loc, r, h, verts=8, rot=(0, 0, 0), r2=None, smooth=False):
    if r2 is None:
        return prim('cylinder', col, loc, rot, smooth=smooth, vertices=verts, radius=r, depth=h)
    return prim('cone', col, loc, rot, smooth=smooth, vertices=verts, radius1=r, radius2=r2, depth=h)


def sphere(col, loc, r, scale=(1, 1, 1), seg=8, rings=6, smooth=True, rot=(0, 0, 0)):
    return prim('uv_sphere', col, loc, rot, scale, smooth=smooth, segments=seg, ring_count=rings, radius=r)


def ico(col, loc, r, scale=(1, 1, 1), sub=1):
    return prim('ico_sphere', col, loc, (0, 0, 0), scale, smooth=False, subdivisions=sub, radius=r)


def between(col, a, b, r, verts=6, r2=None):
    a, b = Vector(a), Vector(b); d = b - a
    rot = d.to_track_quat('Z', 'Y').to_euler()
    return cyl(col, tuple((a + b) / 2), r, d.length, verts, tuple(rot), r2)


def mesh_from(verts, faces, col):
    me = bpy.data.meshes.new('m'); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new('o', me); bpy.context.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return finish(o, col)


def loft(rings, col, cap_bot=True, cap_top=True):
    n = len(rings[0]); verts = [p for r in rings for p in r]; faces = []
    for k in range(len(rings) - 1):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap_bot: faces.append(tuple(reversed(range(n))))
    if cap_top: faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return mesh_from(verts, faces, col)


def extrude_xz(pts, y0, y1, col):
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh_from(verts, faces, col)


ASSETS = {}


def asset(name, parts):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name; o.data.name = name
    ASSETS[name] = o
    return o


# ---------------- jet ski (frente = +Y) ----------------
HULL = [(0, 1.9), (0.5, 1.45), (0.62, 0.5), (0.62, -0.6), (0.58, -1.2), (0.4, -1.38), (-0.4, -1.38), (-0.58, -1.2), (-0.62, -0.6), (-0.62, 0.5), (-0.5, 1.45)]
def ring(k, z, back=0.0):
    return [(x * k, (y - back) if y > 0 else y * (0.85 + 0.15 * k), z) for x, y in HULL]
p = []
p.append(loft([ring(0.62, 0.0, 0.45), ring(1.0, 0.3)], FOLHA_ESC, cap_top=False))
p.append(loft([ring(1.0, 0.3), ring(1.02, 0.4)], LIMA, cap_bot=False, cap_top=False))
p.append(loft([ring(1.02, 0.4), ring(0.9, 0.66)], BRANCO, cap_bot=False))
p.append(box(TINTA, (0, -0.38, 0.8), (0.58, 1.15, 0.28), bevel=0.05))
p.append(box(LIMA, (0, 0.62, 0.84), (0.82, 0.62, 0.42), rot=(0.45, 0, 0), bevel=0.04))
p.append(box(VIDRO, (0, 0.88, 1.08), (0.7, 0.06, 0.3), rot=(-0.6, 0, 0)))
p.append(cyl(PRETO, (0, 0.45, 1.15), 0.05, 1.25, 6, rot=(0, math.pi / 2, 0)))
for s in (-1, 1): p.append(cyl(LARANJA, (s * 0.56, 0.45, 1.15), 0.075, 0.2, 6, rot=(0, math.pi / 2, 0)))
p.append(cyl(PRETO, (0, -1.45, 0.22), 0.13, 0.25, 8, rot=(math.pi / 2, 0, 0)))
for s in (-1, 1): p.append(box(TINTA, (s * 0.42, 0.1, 0.68), (0.22, 0.75, 0.06)))
asset('jetski', p)

# ---------------- capivarinha piloto ----------------
p = []
p.append(sphere(CAPI, (0, 0.1, 1.38), 1, (0.44, 0.48, 0.55), seg=10, rings=7, rot=(-0.3, 0, 0)))
p.append(cyl(LIMA, (0, 0.14, 1.5), 0.47, 0.38, 10, rot=(-0.3, 0, 0)))
p.append(box(LARANJA, (0, 0.6, 1.52), (0.46, 0.06, 0.1), rot=(-0.3, 0, 0)))
# cabeça quadradona de capivara
p.append(box(CAPI, (0, 0.5, 1.98), (0.56, 0.92, 0.56), rot=(0.08, 0, 0), bevel=0.1))
p.append(box(CAPI_ESC, (0, 0.95, 1.9), (0.44, 0.14, 0.32), bevel=0.05))
for s in (-1, 1): p.append(box(CAPI_FOCINHO, (s * 0.08, 1.02, 1.98), (0.07, 0.04, 0.06)))
for s in (-1, 1):
    p.append(sphere(PRETO, (s * 0.27, 0.72, 2.1), 0.055, seg=6, rings=4))
    p.append(sphere(BRANCO, (s * 0.29, 0.75, 2.12), 0.018, seg=4, rings=3))
    p.append(sphere(CAPI_ESC, (s * 0.2, 0.22, 2.28), 0.09, (1, 0.6, 1), seg=6, rings=4))
# a laranja na cabeça
p.append(sphere(LARANJA, (0, 0.4, 2.42), 0.17, seg=8, rings=6))
p.append(box(FOLHA_ESC, (0.07, 0.4, 2.62), (0.16, 0.06, 0.03), rot=(0, 0.5, 0)))
# braços até o guidão, pernas no apoio de pé
for s in (-1, 1):
    p.append(between(CAPI, (s * 0.36, 0.38, 1.62), (s * 0.5, 0.46, 1.2), 0.09))
    p.append(sphere(CAPI_ESC, (s * 0.52, 0.46, 1.16), 0.1, seg=6, rings=4))
    p.append(between(CAPI, (s * 0.26, -0.05, 1.05), (s * 0.4, 0.42, 1.0), 0.13))
    p.append(between(CAPI, (s * 0.4, 0.42, 1.0), (s * 0.42, 0.45, 0.72), 0.1))
    p.append(box(CAPI_FOCINHO, (s * 0.42, 0.5, 0.7), (0.16, 0.24, 0.06)))
asset('capivara', p)

# ---------------- araucária (origem na base, ~18 m) ----------------
p = [cyl(MADEIRA, (0, 0, 8), 0.45, 16, 6, r2=0.25)]
for tier, (n, zr, L) in enumerate([(7, 15.6, 3.6), (5, 14.4, 2.6)]):
    for i in range(n):
        a = i / n * math.tau + tier * 0.4
        end = (math.cos(a) * L, math.sin(a) * L, zr + 1.4)
        p.append(between(MADEIRA, (0, 0, zr), end, 0.12, 5))
        p.append(cyl(FOLHA_ESC if tier == 0 else TINTA, (end[0], end[1], end[2] + 0.3), 1.7, 0.9, 7, r2=0.6))
p.append(cyl(FOLHA_ESC, (0, 0, 16.9), 1.6, 0.8, 7, r2=0.5))
asset('araucaria', p)

# ---------------- árvores de rua: plátano verde, ipê amarelo, ipê roxo ----------------
for name, cols in [('arvore_verde', (FOLHA, FOLHA_ESC)), ('ipe_amarelo', (AMARELO, 0xe0a820)), ('ipe_roxo', (LILAS, 0x86449c))]:
    p = [cyl(MADEIRA, (0, 0, 2.6), 0.3, 5.2, 6, r2=0.2)]
    p.append(between(MADEIRA, (0, 0, 4.2), (1.1, 0.3, 6.2), 0.12, 5))
    p.append(between(MADEIRA, (0, 0, 4.6), (-1.0, -0.5, 6.5), 0.12, 5))
    p.append(ico(cols[0], (0, 0, 7.0), 2.5))
    p.append(ico(cols[1], (1.4, 0.4, 6.6), 1.8))
    p.append(ico(cols[0], (-1.2, -0.6, 7.3), 1.9))
    asset(name, p)

# ---------------- poste da Copel (origem na base; travessa no eixo X) ----------------
p = [cyl(CINZA, (0, 0, 5), 0.22, 10, 8, r2=0.14)]
p.append(box(CINZA_ESC, (0, 0, 9.3), (2.3, 0.15, 0.15)))
for x in (-0.95, 0, 0.95): p.append(cyl(BRANCO, (x, 0, 9.48), 0.06, 0.2, 6))
p.append(cyl(0x7d8076, (0, -0.42, 7.6), 0.34, 0.95, 8))
p.append(box(PRETO, (0, -0.2, 7.6), (0.1, 0.3, 0.1)))
p.append(box(AMARELO, (0, 0.17, 2.4), (0.3, 0.04, 0.3)))
asset('poste', p)

# ---------------- galho (comprimento no eixo X) ----------------
p = [between(MADEIRA, (-3.75, 0, 0), (3.75, 0, 0), 0.3, 6, r2=0.18)]
for x, s in [(-2, 1), (0.5, -1), (2.5, 1)]:
    p.append(between(MADEIRA, (x, 0, 0), (x + 0.7, s * 0.9, 1.6), 0.11, 5))
    p.append(ico(FOLHA, (x + 0.8, s * 1.1, 1.9), 1.15))
p.append(ico(FOLHA_ESC, (3.9, 0, 0.3), 1.5))
asset('galho', p)

# ---------------- pinhão (semente da araucária: gota alongada, levemente curva, casca castanho-avermelhada,
# ponta escura e a base clara onde ela se prendia na pinha) ----------------
PIN_CASCA, PIN_CLARO, PIN_PONTA, PIN_BASE = 0x8c3b1e, 0xb5582c, 0x3b1a0c, 0xe8d3a8
N = 10
prof = [(-1.0, 0.0), (-0.96, 0.2), (-0.85, 0.34), (-0.6, 0.42), (-0.2, 0.44), (0.2, 0.4), (0.55, 0.3), (0.8, 0.18), (0.95, 0.07), (1.05, 0.0)]
verts, faces, cols = [], [], []
for k, (z, r) in enumerate(prof):
    bend = 0.12 * (z + 1) ** 2 / 4  # curvinha para um lado
    for a in range(N):
        ang = a / N * math.tau
        verts.append((math.cos(ang) * r * 0.92 + bend, math.sin(ang) * r * 0.72, z))
for k in range(len(prof) - 1):
    for a in range(N):
        i0, i1 = k * N + a, k * N + (a + 1) % N
        faces.append((i0, i1, i1 + N, i0 + N))
o = mesh_from(verts, faces, PIN_CASCA)
ca = o.data.color_attributes['Col']
for poly in o.data.polygons:
    zc = sum(o.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
    xc = sum(o.data.vertices[v].co.x for v in poly.vertices) / len(poly.vertices)
    c = PIN_BASE if zc < -0.82 else PIN_PONTA if zc > 0.78 else (PIN_CLARO if xc > 0.18 else PIN_CASCA)
    for li in poly.loop_indices: ca.data[li].color_srgb = hexc(c)
for poly in o.data.polygons: poly.use_smooth = True
asset('pinhao', [o])

# ---------------- a onda que persegue (crista curvada, 20 m de largura no eixo X, frente para +Y) ----------------
AGUA_ESC, AGUA_MED, ESPUMA = 0x1f6f5c, 0x3f9a80, 0xf4f8f2
prof = [(-6, 0), (-3, 2.2), (-0.5, 5.2), (1.4, 7.2), (2.8, 7.6), (3.6, 6.8), (3.4, 5.6), (2.6, 5.4)]
verts, faces = [], []
W = 11
for xi in range(-W, W + 1, 2):
    amp = 1 - (abs(xi) / (W + 2)) ** 3
    for y, z in prof: verts.append((xi, y * (0.85 + 0.15 * amp), z * amp + 0.1 * math.sin(xi)))
n = len(prof); cols_n = W + 1
for c in range(cols_n - 1):
    for k in range(n - 1):
        a = c * n + k; faces.append((a, a + 1, a + 1 + n, a + n))
o = mesh_from(verts, faces, AGUA_MED)
ca = o.data.color_attributes['Col']
for poly in o.data.polygons:
    zc = sum(o.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
    yc = sum(o.data.vertices[v].co.y for v in poly.vertices) / len(poly.vertices)
    c = ESPUMA if (zc > 5.6 or yc > 2.6) else AGUA_MED if zc > 2.5 else AGUA_ESC
    for li in poly.loop_indices: ca.data[li].color_srgb = hexc(c)
p = [o]
for xi in range(-W + 1, W, 3): p.append(ico(ESPUMA, (xi + 0.5, 2.9, 7.2), 0.9, sub=1))
asset('onda', p)

# ---------------- saco de lixo (cinza claro: o jogo tinge por instância) ----------------
p = [ico(0xdedede, (0, 0, 0), 0.5, (1, 0.9, 0.75))]
p.append(cyl(0xc8c8c8, (0, 0, 0.42), 0.12, 0.25, 6, r2=0.04))
asset('lixo', p)

# ---------------- cone ----------------
p = [box(PRETO, (0, 0, 0.05), (0.95, 0.95, 0.1))]
p.append(cyl(LARANJA, (0, 0, 0.72), 0.42, 1.25, 8, r2=0.06))
p.append(cyl(BRANCO, (0, 0, 0.75), 0.27, 0.2, 8, r2=0.23))
asset('cone', p)

# ---------------- biarticulado de Curitiba: 3 seções vermelhas articuladas, sanfonas pretas, frente com para-brisa
# grande e letreiro, portas à esquerda (embarque nas estações-tubo), ar-condicionado no teto.
# Comprimento no eixo Y; a frente do ônibus fica em -Y (vira +Z no jogo, de frente para quem vem).
VERM_BUS, VERM_ESC, PRATA_B = 0xd2322f, 0x9e2422, 0xb8bcc2
def secao_bus(front=False, rear=False, sanfona=True):
    p = []
    p.append(box(VERM_BUS, (0, 0, 0.15), (2.6, 9.2, 2.5), bevel=0.12))
    p.append(box(VERM_ESC, (0, 0, -1.05), (2.64, 9.0, 0.35)))
    p.append(box(PRATA_B, (0, 0, 1.45), (2.5, 9.0, 0.22), bevel=0.06))
    # faixa de janelas com colunas
    for sx in (-1, 1):
        p.append(box(VIDRO, (sx * 1.31, 0, 0.45), (0.05, 8.6, 0.95)))
        for k in range(7): p.append(box(VERM_BUS, (sx * 1.33, -4.0 + k * 1.33, 0.45), (0.05, 0.14, 0.98)))
        p.append(box(BRANCO, (sx * 1.33, 0, -0.55), (0.04, 8.8, 0.12)))
    # portas do lado esquerdo (x negativo), para as estações-tubo
    for y in (-2.2, 2.2):
        p.append(box(PRATA_B, (-1.34, y, 0.0), (0.05, 1.5, 2.1)))
        p.append(box(VIDRO, (-1.36, y - 0.38, 0.2), (0.04, 0.6, 1.5))); p.append(box(VIDRO, (-1.36, y + 0.38, 0.2), (0.04, 0.6, 1.5)))
    # ar-condicionado no teto
    p.append(box(BRANCO, (0, 1.5 if front else 0, 1.72), (1.6, 2.6, 0.32), bevel=0.06))
    # rodas
    for y in ((-3.0, 2.8) if (front or rear) else (2.8,)):
        for sx in (-1, 1):
            p.append(cyl(PRETO, (sx * 1.22, y, -1.05), 0.52, 0.32, 12, rot=(0, math.pi / 2, 0)))
            p.append(cyl(PRATA_B, (sx * 1.39, y, -1.05), 0.26, 0.04, 8, rot=(0, math.pi / 2, 0)))
    if front:
        p.append(box(VIDRO, (0, -4.62, 0.55), (2.3, 0.08, 1.5), rot=(0.12, 0, 0)))
        p.append(box(PRETO, (0, -4.66, 1.42), (2.0, 0.06, 0.32)))
        p.append(box(AMARELO, (0, -4.69, 1.42), (1.5, 0.04, 0.18)))
        p.append(box(PRETO, (0, -4.66, -0.85), (2.6, 0.18, 0.4)))
        for sx in (-1, 1):
            p.append(box(0xfff2c4, (sx * 0.95, -4.68, -0.45), (0.45, 0.04, 0.22)))
            p.append(box(PRETO, (sx * 1.38, -4.3, 0.95), (0.05, 0.35, 0.06)))
    if rear:
        p.append(box(VIDRO, (0, 4.62, 0.5), (2.2, 0.06, 0.9)))
        for sx in (-1, 1): p.append(box(VERMELHO, (sx * 1.0, 4.66, -0.5), (0.35, 0.04, 0.45)))
        p.append(box(PRETO, (0, 4.62, -0.85), (2.6, 0.16, 0.38)))
    if sanfona:
        for k in range(5): p.append(box(PRETO if k % 2 == 0 else CINZA_ESC, (0, 4.66 + k * 0.08, 0.2), (2.4 - (k % 2) * 0.1, 0.08, 2.5)))
    return p
asset('bi_frente', secao_bus(front=True))
asset('bi_meio', secao_bus())
asset('bi_tras', secao_bus(rear=True, sanfona=False))

# ---------------- estação-tubo (eixo Y) ----------------
p = [box(CINZA, (0, 0, 0.5), (3.4, 12.4, 0.6))]
for y in [-6 + i * 1.5 for i in range(9)]:
    prim('torus', CINZA_ESC, (0, y, 2.2), (math.pi / 2, 0, 0), major_radius=1.64, minor_radius=0.07, major_segments=12, minor_segments=4)
    p.append(bpy.context.active_object)
p.append(box(CINZA_ESC, (0, 0, 3.85), (0.5, 12.2, 0.12)))
for s in (-1, 1): p.append(box(CINZA, (0, s * 7.0, 0.35), (1.6, 1.8, 0.3)))
asset('tubo', p)
asset('tubo_vidro', [cyl(0xbfe3ef, (0, 0, 2.2), 1.6, 12, 12, rot=(math.pi / 2, 0, 0))])

# ---------------- lancha da Copel (frente +Y) ----------------
BOAT = [(0, 4.2), (1.0, 3.0), (1.55, 1.2), (1.6, -3.6), (1.3, -4.0), (-1.3, -4.0), (-1.6, -3.6), (-1.55, 1.2), (-1.0, 3.0)]
p = [loft([[(x * 0.7, y * 0.9, 0) for x, y in BOAT], [(x, y, 0.7) for x, y in BOAT]], BRANCO, cap_top=False)]
p.append(loft([[(x, y, 0.7) for x, y in BOAT], [(x * 1.02, y * 1.01, 1.0) for x, y in BOAT]], LARANJA, cap_bot=False))
p.append(box(BRANCO, (0, -1.4, 1.9), (2.4, 2.6, 1.8), bevel=0.06))
p.append(box(VIDRO, (0, -1.4, 2.3), (2.46, 2.0, 0.6)))
p.append(box(LARANJA, (0, -1.4, 2.88), (2.5, 2.7, 0.15)))
p.append(between(LARANJA, (0, 1.2, 1.0), (0, 2.6, 4.2), 0.16, 6))
p.append(between(LARANJA, (0, 2.6, 4.2), (0, 3.6, 3.4), 0.12, 6))
BOLT = [(-0.15, 0.55), (0.25, 0.55), (0.05, 0.1), (0.3, 0.1), (-0.2, -0.6), (-0.02, -0.08), (-0.28, -0.08)]
for s in (-1, 1):
    p.append(box(AMARELO, (s * 1.24, -1.4, 1.5), (0.04, 0.9, 0.6)))
asset('lancha_copel', p)

# ---------------- fusível (caixa amarela com raio) ----------------
p = [box(AMARELO, (0, 0, 0), (1.4, 1.4, 1.4), bevel=0.08)]
p.append(box(VIDRO, (0, 0, 0), (1.44, 1.44, 0.35)))
p.append(extrude_xz([(x * 1.0, z) for x, z in BOLT], -0.75, -0.69, TINTA))
p.append(extrude_xz([(x * 1.0, z) for x, z in BOLT], 0.69, 0.75, TINTA))
asset('fusivel', p)

# ================= mobiliário e cenário do percurso =================
PEDRA, PEDRA_ESC, AGUA = 0xe2dcc6, 0xbdb59a, 0x9fd3e0

# lixeiras da coleta seletiva (papel, plástico, vidro, metal), largura no eixo X
p = [box(CINZA_ESC, (0, 0, 1.05), (2.3, 0.12, 0.12)), box(CINZA_ESC, (-1.15, 0, 0.55), (0.1, 0.1, 1.1)), box(CINZA_ESC, (1.15, 0, 0.55), (0.1, 0.1, 1.1))]
for i, c in enumerate([JEANS, VERMELHO, FOLHA_ESC, AMARELO]):
    x = -0.82 + i * 0.55
    p.append(box(c, (x, 0, 0.62), (0.46, 0.46, 0.8), bevel=0.03))
    p.append(box(BRANCO, (x, -0.235, 0.78), (0.3, 0.02, 0.12)))
asset('lixeiras', p)

# banco de praça
p = [box(MADEIRA, (0, 0, 0.5), (2.0, 0.5, 0.08)), box(MADEIRA, (0, 0.24, 0.85), (2.0, 0.08, 0.4))]
for x in (-0.85, 0.85): p += [box(PRETO, (x, 0, 0.25), (0.08, 0.5, 0.5)), box(PRETO, (x, 0.24, 0.7), (0.08, 0.06, 0.5))]
asset('banco', p)

# luminária (braço para +X)
p = [cyl(TINTA, (0, 0, 3.5), 0.13, 7, 8, r2=0.08), box(TINTA, (0, 0, 0.3), (0.4, 0.4, 0.6))]
p.append(between(TINTA, (0, 0, 6.8), (0.9, 0, 7.4), 0.06, 6))
p.append(between(TINTA, (0.9, 0, 7.4), (1.8, 0, 7.3), 0.06, 6))
p.append(box(CINZA_ESC, (1.9, 0, 7.2), (0.7, 0.35, 0.18), bevel=0.04))
p.append(box(0xfff2c4, (1.9, 0, 7.09), (0.55, 0.26, 0.04)))
asset('luminaria', p)

# placa de rua: poste + painel (o jogo cola o nome por cima, na face -Y do Blender = +Z no jogo)
p = [cyl(CINZA, (0, 0, 1.6), 0.06, 3.2, 6)]
p.append(box(BRANCO, (0, 0, 3.15), (2.3, 0.1, 0.62)))
p.append(box(TINTA, (0, 0, 3.15), (2.2, 0.12, 0.52)))
asset('placa', p)

# boia
prim('torus', LARANJA, (0, 0, 0.15), (0, 0, 0), major_radius=0.55, minor_radius=0.17, major_segments=10, minor_segments=5)
p = [bpy.context.active_object]
for a in range(4):
    ang = a / 4 * math.tau
    p.append(box(BRANCO, (math.cos(ang) * 0.55, math.sin(ang) * 0.55, 0.15), (0.2, 0.38, 0.38), rot=(0, 0, ang)))
asset('boia', p)

# marreco (frente +Y)
p = [sphere(0x8a6a4a, (0, 0, 0.25), 1, (0.22, 0.38, 0.2), seg=8, rings=5)]
p.append(sphere(FOLHA_ESC, (0, 0.3, 0.5), 0.13, seg=6, rings=4))
p.append(cyl(LARANJA, (0, 0.46, 0.48), 0.05, 0.16, 4, rot=(-math.pi / 2, 0, 0), r2=0.02))
p.append(box(BRANCO, (0, 0.24, 0.4), (0.2, 0.06, 0.04)))
p.append(cyl(CREME, (0, -0.4, 0.33), 0.08, 0.16, 4, rot=(math.pi / 2.6, 0, 0), r2=0.01))
for s in (-1, 1): p.append(sphere(PRETO, (s * 0.07, 0.38, 0.54), 0.02, seg=4, rings=3))
asset('pato', p)

# canoa (frente +Y)
CAN = [(0, 2.0), (0.4, 1.2), (0.5, 0), (0.4, -1.2), (0, -2.0), (-0.4, -1.2), (-0.5, 0), (-0.4, 1.2)]
p = [loft([[(x * 0.5, y * 0.9, 0) for x, y in CAN], [(x, y, 0.45) for x, y in CAN]], MADEIRA, cap_top=False)]
for y in (-0.6, 0.6): p.append(box(0x8a6a4a, (0, y, 0.32), (0.85, 0.2, 0.05)))
asset('canoa', p)

# capivara de enfeite (em pé na água, frente +Y)
p = [sphere(CAPI, (0, 0, 0.75), 1, (0.42, 0.75, 0.42), seg=10, rings=7)]
p.append(box(CAPI, (0, 0.78, 1.05), (0.42, 0.62, 0.42), rot=(0.25, 0, 0), bevel=0.08))
p.append(box(CAPI_ESC, (0, 1.08, 0.95), (0.34, 0.1, 0.26), bevel=0.04))
for s in (-1, 1):
    p.append(sphere(PRETO, (s * 0.2, 0.92, 1.17), 0.045, seg=6, rings=4))
    p.append(sphere(CAPI_ESC, (s * 0.15, 0.55, 1.3), 0.07, (1, 0.6, 1), seg=6, rings=4))
    for y in (-0.4, 0.4): p.append(cyl(CAPI_ESC, (s * 0.22, y, 0.25), 0.09, 0.5, 6))
p.append(sphere(LARANJA, (0, 0.72, 1.4), 0.13, seg=8, rings=6))
asset('capivara_enfeite', p)

# banca de jornal
p = [box(FOLHA, (0, 0, 1.25), (3.0, 2.0, 2.5), bevel=0.05)]
p.append(box(LIMA, (0, 0, 2.6), (3.2, 2.2, 0.2)))
p.append(box(LARANJA, (0, -1.3, 2.35), (3.0, 0.7, 0.08), rot=(0.35, 0, 0)))
p.append(box(CREME, (0, -1.02, 1.2), (2.6, 0.06, 1.5)))
cols = [VERMELHO, JEANS, AMARELO, LILAS, LARANJA, FOLHA_ESC]
for r in range(2):
    for c in range(5):
        p.append(box(cols[(r * 5 + c) % 6], (-1.0 + c * 0.5, -1.07, 0.8 + r * 0.7), (0.36, 0.03, 0.5)))
asset('banca', p)

# tapume de obra (módulo de 3,4 m no eixo X)
p = []
for i in range(6):
    p.append(box(LARANJA if i % 2 == 0 else BRANCO, (-1.42 + i * 0.57, 0, 1.05), (0.57, 0.12, 0.9)))
p += [box(CINZA_ESC, (x, 0, 0.5), (0.1, 0.1, 1.0)) for x in (-1.6, 1.6)]
p += [box(CINZA_ESC, (x, 0, 0.05), (0.2, 0.8, 0.1)) for x in (-1.6, 1.6)]
p.append(box(AMARELO, (0, -0.07, 1.85), (1.4, 0.06, 0.55)))
p.append(box(TINTA, (0, -0.1, 1.85), (1.1, 0.02, 0.14)))
p.append(sphere(AMARELO, (1.6, 0, 1.75), 0.1, seg=6, rings=4))
asset('tapume', p)

# portal de praça (vão de 16 m no eixo X; o jogo escreve o nome na faixa, face -Y)
p = []
for x in (-8.2, 8.2):
    p.append(box(TINTA, (x, 0, 3.8), (0.9, 0.9, 7.6), bevel=0.06))
    p.append(box(LIMA, (x, 0, 0.3), (1.3, 1.3, 0.6)))
    p.append(ico(FOLHA, (x, 0, 8.6), 0.9))
p.append(box(LIMA, (0, 0, 7.4), (17.6, 0.8, 1.2), bevel=0.06))
p.append(box(BRANCO, (0, -0.45, 6.2), (10.5, 0.1, 1.7)))
p.append(box(FOLHA_ESC, (0, -0.42, 6.2), (10.8, 0.06, 1.9)))
asset('portal', p)

# chafariz (Praça Osório)
p = [cyl(PEDRA, (0, 0, 0.4), 3.2, 0.8, 16), cyl(AGUA, (0, 0, 0.82), 2.9, 0.05, 16)]
p.append(cyl(PEDRA_ESC, (0, 0, 1.6), 0.35, 2.4, 8))
p.append(cyl(PEDRA, (0, 0, 2.7), 1.3, 0.35, 12, r2=0.5))
p.append(cyl(AGUA, (0, 0, 3.5), 0.15, 1.2, 8, r2=0.9))
asset('chafariz', p)

# obelisco (Praça 19 de Dezembro)
p = [box(PEDRA_ESC, (0, 0, 0.4), (3.4, 3.4, 0.8)), box(PEDRA, (0, 0, 1.3), (2.2, 2.2, 1.0))]
p.append(loft([[(-0.8, -0.8, 1.8), (0.8, -0.8, 1.8), (0.8, 0.8, 1.8), (-0.8, 0.8, 1.8)], [(-0.45, -0.45, 12), (0.45, -0.45, 12), (0.45, 0.45, 12), (-0.45, 0.45, 12)]], PEDRA, cap_top=False))
p.append(mesh_from([(-0.45, -0.45, 12), (0.45, -0.45, 12), (0.45, 0.45, 12), (-0.45, 0.45, 12), (0, 0, 13.2)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], PEDRA))
asset('obelisco', p)


# ================= marcos reais do trajeto (fachada para -Y do Blender = +Z no jogo) =================
OCRE, OCRE_ESC, TELHA = 0xe6c48a, 0xc9a266, 0x9a4a2a

# Bondinho da Leitura (Rua XV): bonde antigo, comprimento no eixo X
p = [box(TINTA, (0, 0, 1.1), (8.4, 2.4, 1.2), bevel=0.06), box(CREME, (0, 0, 2.35), (8.4, 2.4, 1.3), bevel=0.04)]
for i in range(6): p.append(box(VIDRO, (-3.3 + i * 1.32, -1.22, 2.4), (0.95, 0.06, 0.8)))
p.append(box(CINZA_ESC, (0, 0, 3.15), (8.8, 2.6, 0.3), bevel=0.08))
p.append(box(LIMA, (0, 0, 1.8), (8.45, 2.45, 0.15)))
p.append(between(PRETO, (2.5, 0, 3.3), (0.5, 0, 4.8), 0.04, 4))
for x in (-2.6, 2.6):
    for y in (-0.9, 0.9): p.append(cyl(PRETO, (x, y, 0.4), 0.42, 0.18, 10, rot=(math.pi / 2, 0, 0)))
for x in (-4.3, 4.3): p.append(box(CINZA_ESC, (x, 0, 1.0), (0.3, 1.8, 0.4)))
asset('bondinho', p)

# Locomotiva Baldwin 4-4-0 do Museu Ferroviário (comprimento no eixo X)
p = [cyl(PRETO, (0.6, 0, 2.3), 0.85, 6.0, 12, rot=(0, math.pi / 2, 0))]
p.append(cyl(PRETO, (2.6, 0, 3.6), 0.35, 1.6, 8, r2=0.6))
p.append(cyl(OCRE_ESC, (0.4, 0, 3.3), 0.35, 0.6, 8))
p.append(box(VERMELHO, (-3.0, 0, 2.6), (2.2, 2.4, 2.6)))
p.append(box(PRETO, (-3.0, 0, 4.05), (2.6, 2.7, 0.3)))
p.append(box(VIDRO, (-3.0, -1.22, 3.0), (1.2, 0.05, 0.9)))
for x in (-1.2, 0.6):
    for y in (-0.9, 0.9): p.append(cyl(VERMELHO, (x, y, 1.0), 0.9, 0.15, 12, rot=(math.pi / 2, 0, 0)))
for x in (2.4, 3.3):
    for y in (-0.8, 0.8): p.append(cyl(VERMELHO, (x, y, 0.5), 0.45, 0.15, 10, rot=(math.pi / 2, 0, 0)))
p.append(mesh_from([(3.8, -0.9, 0.1), (3.8, 0.9, 0.1), (4.8, 0, 0.1), (3.8, 0, 1.2)], [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)], VERMELHO))
p.append(box(CINZA_ESC, (0.3, 0, 0.05), (10, 2.4, 0.1)))
asset('locomotiva', p)

# Portão do Passeio Público: pilares de pedra com arco e grade de ferro (largura no eixo X)
p = []
for x in (-3.4, 3.4):
    p.append(box(PEDRA, (x, 0, 3.2), (1.6, 1.6, 6.4)))
    p.append(box(PEDRA_ESC, (x, 0, 6.6), (2.0, 2.0, 0.4)))
    p.append(cyl(PEDRA, (x, 0, 7.3), 0.45, 1.0, 8, r2=0.2))
arcpts = [(math.cos(a) * 2.6, 0, 5.4 + math.sin(a) * 1.6) for a in [k / 8 * math.pi for k in range(9)]]
for a, b in zip(arcpts, arcpts[1:]): p.append(between(PEDRA_ESC, a, b, 0.25, 6))
for i in range(11): p.append(cyl(PRETO, (-2.4 + i * 0.48, 0, 2.6), 0.05, 5.2, 4))
p.append(box(PRETO, (0, 0, 1.2), (5, 0.08, 0.12))); p.append(box(PRETO, (0, 0, 4.4), (5, 0.08, 0.12)))
for s in (-1, 1): p.append(box(PEDRA, (s * 7, 0, 1.1), (5.4, 0.8, 2.2)))
asset('portao_passeio', p)

# Memorial Árabe: octógono branco com arcos e cúpula
p = [cyl(BRANCO, (0, 0, 3), 5, 6, 8), cyl(JEANS, (0, 0, 6.2), 5.3, 0.4, 8)]
for k in range(8):
    a = k / 8 * math.tau + math.pi / 8
    p.append(box(VIDRO, (math.cos(a) * 4.62, math.sin(a) * 4.62, 2.6), (1.5, 0.12, 3.0), rot=(0, 0, a + math.pi / 2)))
p.append(sphere(JEANS, (0, 0, 6.4), 3.2, (1, 1, 0.9), seg=10, rings=6))
p.append(cyl(AMARELO, (0, 0, 9.6), 0.08, 1.2, 4))
p.append(cyl(BRANCO, (5.5, 3, 6), 0.9, 12, 8))
p.append(cyl(JEANS, (5.5, 3, 12.6), 1.0, 1.4, 8, r2=0.1))
asset('memorial_arabe', p)

# Ruínas de São Francisco: muros de pedra com arcos e topo irregular
PEDRA_R = 0x8a7a62
p = []
for i, (x, h) in enumerate([(-8, 5.5), (-4, 7.0), (0, 6.2), (4, 7.4), (8, 4.6)]):
    p.append(box(PEDRA_R if i % 2 else 0x9c8b70, (x, 0, h / 2), (4.0, 1.4, h)))
for x in (-6, -2, 2, 6):
    p.append(box(0x2f3a2f, (x, -0.72, 2.0), (1.6, 0.1, 3.0)))
    arcp = [(x + math.cos(a) * 0.8, -0.75, 3.5 + math.sin(a) * 0.8) for a in [k / 6 * math.pi for k in range(7)]]
    for a, b in zip(arcp, arcp[1:]): p.append(between(0x2f3a2f, a, b, 0.12, 4))
for x, z in [(-9, 0.3), (-3, 0.3), (5, 0.3), (9.5, 0.3)]: p.append(ico(FOLHA, (x, -1.2, z), 0.9))
p.append(box(PEDRA_R, (-11, 3, 2.2), (1.4, 6, 4.4)))
asset('ruinas', p)


# ================= marcos e ícones v2 (refeitos a partir de referências reais; fachada para -Y) =================
VIDRO_CLARO, DOURADO, MADEIRA_ESC, CONCRETO, CONCRETO_ESC = 0xa8d8e6, 0xd9a52a, 0x5a3820, 0xb9b6ac, 0x8e8b82

def arc_tube(col, cx, cy, cz, R, r, axis='x', a0=0.0, a1=math.pi, n=10, verts=5, sx=1.0):
    """arco feito de segmentos de tubo; axis = eixo perpendicular ao plano do arco"""
    out = []
    pts = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        u, v = math.cos(a) * R * sx, math.sin(a) * R
        pts.append((cx, cy + u, cz + v) if axis == 'x' else (cx + u, cy, cz + v))
    for a, b in zip(pts, pts[1:]): out.append(between(col, a, b, r, verts))
    return out

def grade(col, x0, x1, z0, z1, y, nx, nz, r=0.06):
    """caixilhos de uma fachada de vidro (barras finas)"""
    out = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx; out.append(box(col, (x, y, (z0 + z1) / 2), (r * 2, r * 2, z1 - z0)))
    for j in range(nz + 1):
        z = z0 + (z1 - z0) * j / nz; out.append(box(col, ((x0 + x1) / 2, y, z), (x1 - x0, r * 2, r * 2)))
    return out

# ---------- Jardim Botânico: estufa art nouveau de ferro e vidro (inspirada no Palácio de Cristal), cúpula de 18 m,
# três corpos com coberturas em abóbada e o jardim francês geométrico na frente ----------
p = [box(BRANCO, (0, 0, 0.25), (26, 12, 0.5))]
# corpo central alto com abóbada e cúpula
p.append(box(VIDRO_CLARO, (0, 0, 4.0), (9, 9, 7)))
p.append(cyl(VIDRO_CLARO, (0, 0, 7.5), 4.5, 9, 14, rot=(math.pi / 2, 0, 0)))
p.append(cyl(VIDRO_CLARO, (0, 0, 7.5), 4.5, 9, 14, rot=(0, math.pi / 2, 0)))
p.append(sphere(VIDRO_CLARO, (0, 0, 11.5), 3.6, (1, 1, 1.15), seg=12, rings=7))
p.append(cyl(BRANCO, (0, 0, 15.6), 0.9, 1.2, 8))
p.append(cyl(BRANCO, (0, 0, 16.6), 0.5, 1.0, 8, r2=0.05))
for k in range(8):
    a = k / 8 * math.tau
    p.append(between(BRANCO, (math.cos(a) * 3.6, math.sin(a) * 3.6, 11.4), (math.cos(a) * 0.8, math.sin(a) * 0.8, 15.2), 0.07, 4))
# alas laterais mais baixas com abóbada
for s in (-1, 1):
    p.append(box(VIDRO_CLARO, (s * 8.5, 0, 2.8), (8, 7, 5)))
    p.append(cyl(VIDRO_CLARO, (s * 8.5, 0, 5.3), 3.5, 8, 12, rot=(0, math.pi / 2, 0)))
    for x in range(-3, 4, 2): p += arc_tube(BRANCO, s * 8.5 + x, 0, 5.3, 3.55, 0.07, 'x', 0, math.pi, 8)
    p += grade(BRANCO, s * 8.5 - 4, s * 8.5 + 4, 0.5, 5.3, -3.55, 8, 4)
# caixilhos do corpo central
p += grade(BRANCO, -4.5, 4.5, 0.5, 7.5, -4.55, 9, 6)
for x in (-3, -1, 1, 3): p += arc_tube(BRANCO, x, 0, 7.5, 4.55, 0.07, 'x', 0, math.pi, 9)
p.append(box(BRANCO, (0, -4.6, 2.0), (2.4, 0.2, 3.4)))
# jardim francês: canteiros geométricos coloridos, caminho e fonte
p.append(box(0xd8cfb4, (0, -10.5, 0.08), (3.0, 9, 0.16)))
for row in range(2):
    for s in (-1, 1):
        y = -8 - row * 4.5
        p.append(box(FOLHA, (s * 6.5, y, 0.12), (9, 4.2, 0.24)))
        for k, c in enumerate([VERMELHO, AMARELO, LILAS, VERMELHO, BRANCO]):
            p.append(box(c, (s * (3.2 + k * 1.6), y, 0.28), (1.0, 3.2 if k % 2 else 2.2, 0.12)))
p.append(cyl(PEDRA, (0, -10.2, 0.3), 1.6, 0.6, 12)); p.append(cyl(AGUA, (0, -10.2, 0.62), 1.4, 0.05, 12)); p.append(cyl(AGUA, (0, -10.2, 1.4), 0.12, 1.6, 6, r2=0.5))
asset('jardim_botanico', p)

# ---------- Ópera de Arame: teatro circular de tubos de aço e cobertura transparente, sobre o lago de uma pedreira,
# com passarela de acesso e paredões de rocha atrás ----------
p = [cyl(AGUA, (0, 0, 0.05), 14, 0.1, 24)]
p.append(cyl(BRANCO, (0, 0, 0.6), 7.2, 0.4, 20))
for k in range(20):
    a = k / 20 * math.tau
    p.append(cyl(BRANCO, (math.cos(a) * 7, math.sin(a) * 7, 4.2), 0.12, 7, 4))
    a2 = (k + 1) / 20 * math.tau
    p.append(between(BRANCO, (math.cos(a) * 7, math.sin(a) * 7, 0.8), (math.cos(a2) * 7, math.sin(a2) * 7, 7.6), 0.05, 3))
for z in (0.8, 3.0, 5.4, 7.7):
    prim('torus', BRANCO, (0, 0, z), (0, 0, 0), major_radius=7, minor_radius=0.09, major_segments=20, minor_segments=3); p.append(bpy.context.active_object)
p.append(cyl(VIDRO_CLARO, (0, 0, 9.4), 7.6, 3.4, 20, r2=1.0))
for k in range(10):
    a = k / 10 * math.tau
    p.append(between(BRANCO, (math.cos(a) * 7.6, math.sin(a) * 7.6, 7.7), (math.cos(a) * 1.0, math.sin(a) * 1.0, 11.1), 0.08, 4))
p.append(cyl(BRANCO, (0, 0, 11.7), 0.9, 1.2, 8, r2=0.3))
# passarela até a margem
p.append(box(BRANCO, (0, -10.5, 0.6), (2.4, 7, 0.2)))
for s in (-1, 1):
    p.append(box(BRANCO, (s * 1.2, -10.5, 1.1), (0.08, 7, 0.08)))
    for y in range(-13, -7, 2): p.append(box(BRANCO, (s * 1.2, y, 0.85), (0.08, 0.08, 0.5)))
# paredões da pedreira e mata atrás
for k, (x, h, w) in enumerate([(-14, 9, 6), (-8, 12, 7), (0, 14, 8), (8, 11, 7), (14, 8, 6)]):
    p.append(box(0x8c8a80 if k % 2 else 0x7a786f, (x, 13, h / 2), (w, 4, h)))
    p.append(ico(FOLHA_ESC, (x, 13, h + 0.8), 2.2))
for x in (-12, -4, 5, 12): p.append(ico(FOLHA, (x, 9, 1.2), 1.8))
asset('opera_arame', p)

# ---------- Torre Panorâmica (antiga Torre da Telepar): fuste de concreto, mirante envidraçado no topo,
# plataformas de antenas e mastro listrado (109,5 m na real; aqui em escala de jogo) ----------
p = [cyl(CONCRETO, (0, 0, 1.0), 4.5, 2.0, 12), cyl(BRANCO, (0, 0, 2.6), 3.2, 1.2, 12)]
p.append(cyl(CONCRETO, (0, 0, 20), 2.0, 34, 12, r2=1.4))
for z in (8, 16, 24, 32): p.append(cyl(CONCRETO_ESC, (0, 0, z), 2.0 - z * 0.017, 0.3, 12))
p.append(cyl(CONCRETO, (0, 0, 37.5), 3.2, 1.0, 14, r2=4.6))
p.append(cyl(VIDRO, (0, 0, 39.4), 4.7, 2.8, 16))
for k in range(16):
    a = k / 16 * math.tau; p.append(box(BRANCO, (math.cos(a) * 4.72, math.sin(a) * 4.72, 39.4), (0.18, 0.18, 2.8), rot=(0, 0, a)))
p.append(cyl(BRANCO, (0, 0, 41.1), 5.0, 0.6, 16))
p.append(cyl(CONCRETO, (0, 0, 43), 2.2, 3.2, 12))
for z, r in ((45.2, 3.2), (48.6, 2.4)):
    p.append(cyl(CINZA_ESC, (0, 0, z), r, 0.5, 12))
    for k in range(6):
        a = k / 6 * math.tau; p.append(box(BRANCO, (math.cos(a) * r * 0.8, math.sin(a) * r * 0.8, z + 1.0), (0.7, 0.3, 1.6), rot=(0, 0, a)))
p.append(cyl(CINZA, (0, 0, 47), 1.2, 4, 10))
for i in range(6): p.append(cyl(VERMELHO if i % 2 == 0 else BRANCO, (0, 0, 49.5 + i * 1.6), 0.45 - i * 0.05, 1.6, 8))
p.append(sphere(VERMELHO, (0, 0, 59.4), 0.3, seg=6, rings=4))
asset('torre_panoramica', p)

# ---------- Museu Oscar Niemeyer: o "Olho" (lente de vidro escuro com aro branco) sobre o pilar amarelo,
# rampa branca sinuosa e o prédio comprido atrás, com espelho d'água ----------
p = [box(BRANCO, (0, 16, 4.5), (46, 14, 9))]
for i in range(15): p.append(box(VIDRO, (-21 + i * 3, 8.95, 5.5), (1.6, 0.1, 4.2)))
p.append(box(BRANCO, (0, 16, 0.5), (48, 16, 1.0)))
p.append(box(AGUA, (0, -7, 0.06), (40, 10, 0.12)))
# pilar amarelo de seção trapezoidal
p.append(loft([[(-3.2, -3.2, 0), (3.2, -3.2, 0), (3.2, 3.2, 0), (-3.2, 3.2, 0)], [(-4.6, -2.2, 9.5), (4.6, -2.2, 9.5), (4.6, 2.2, 9.5), (-4.6, 2.2, 9.5)]], AMARELO))
# a lente: elipsoide achatado com aro
p.append(sphere(VIDRO, (0, 0, 14.5), 1, (17, 6.5, 4.2), seg=20, rings=10, smooth=True))
prim('torus', BRANCO, (0, 0, 14.5), (math.pi / 2, 0, 0), major_radius=1.0, minor_radius=0.03, major_segments=24, minor_segments=4)
o = bpy.context.active_object; o.scale = (17.1, 4.3, 1); finish(o, BRANCO); p.append(o)
# rampa branca curva ligando ao prédio
for k in range(10):
    a = k / 9 * math.pi
    p.append(box(BRANCO, (-12 + math.cos(a) * 6, 4 + math.sin(a) * 3, 0.5 + k * 0.55), (2.6, 1.6, 0.3), rot=(0, 0, a)))
asset('museu_olho', p)

# ---------- Rua 24 Horas: galeria com arcos tubulares brancos cobertos de vidro e um relógio grande
# de 24 horas em cada fachada (comprimento no eixo X) ----------
L = 26
p = [box(0xd8d3c4, (0, 0, 0.15), (L + 2, 12, 0.3))]
for i in range(14):
    x = -L / 2 + i * L / 13
    p += arc_tube(BRANCO, x, 0, 3.2, 5.6, 0.16, 'x', 0, math.pi, 10, 6, 1.0)
    for s in (-1, 1): p.append(cyl(BRANCO, (x, s * 5.6, 1.6), 0.16, 3.2, 6))
p.append(cyl(VIDRO_CLARO, (0, 0, 3.2), 5.5, L, 14, rot=(0, math.pi / 2, 0)))
for s in (-1, 1): p.append(box(VIDRO_CLARO, (0, s * 5.5, 1.6), (L, 0.06, 3.2)))
for s in (-1, 1):
    x = s * (L / 2 + 0.2)
    p.append(box(BRANCO, (x, 0, 9.4), (0.6, 4.4, 4.4), bevel=0.1))
    p.append(cyl(BRANCO, (x + s * 0.32, 0, 9.4), 1.85, 0.12, 24, rot=(0, math.pi / 2, 0)))
    for k in range(24):
        a = k / 24 * math.tau; p.append(box(PRETO if k % 6 == 0 else CINZA_ESC, (x + s * 0.4, math.cos(a) * 1.55, 9.4 + math.sin(a) * 1.55), (0.05, 0.12, 0.25 if k % 6 == 0 else 0.12)))
    p.append(box(PRETO, (x + s * 0.42, 0, 9.9), (0.05, 0.12, 1.1))); p.append(box(PRETO, (x + s * 0.42, 0.5, 9.4), (0.05, 1.1, 0.1)))
    p.append(box(BRANCO, (x, 0, 7.0), (0.5, 1.2, 1.2)))
# a fachada fica de lado para a pista: placa com faixa lima no comprido
p.append(box(LIMA, (0, -5.8, 6.6), (12, 0.15, 0.9)))
asset('rua_24h', p)

# ---------- Memorial Ucraniano: réplica de madeira da igreja de São Miguel Arcanjo (Serra do Tigre, Mallet),
# estilo bizantino, cúpulas douradas, campanário de madeira e a pêssanka gigante ----------
p = []
p.append(box(MADEIRA, (0, 0, 3.0), (6, 12, 6)))
p.append(box(MADEIRA, (0, 0, 3.0), (12, 6, 6)))
for (x, y, w, d) in [(0, 0, 6.6, 12.6), (0, 0, 12.6, 6.6)]:
    p.append(box(MADEIRA_ESC, (x, y, 6.2), (w, d, 0.4)))
p.append(box(MADEIRA, (0, 0, 8.0), (5, 5, 3.6)))
p.append(cyl(MADEIRA, (0, 0, 10.4), 2.2, 1.4, 8))
for (x, y, z, r) in [(0, 0, 12.4, 2.0), (0, -4.6, 8.4, 1.1), (0, 4.6, 8.4, 1.1), (-4.6, 0, 8.4, 1.1), (4.6, 0, 8.4, 1.1)]:
    if z < 10: p.append(cyl(MADEIRA, (x, y, z - 1.2), r * 0.85, 1.2, 8))
    p.append(sphere(DOURADO, (x, y, z), r, (1, 1, 1.3), seg=10, rings=7))
    p.append(cyl(DOURADO, (x, y, z + r * 1.4), r * 0.25, r * 0.9, 6, r2=0.02))
    p.append(box(DOURADO, (x, y, z + r * 2.1), (0.08, 0.08, 0.8))); p.append(box(DOURADO, (x, y, z + r * 2.2), (0.5, 0.08, 0.08)))
for k in range(5): p.append(box(MADEIRA_ESC, (0, -6.05, 0.8 + k * 1.1), (5.8, 0.1, 0.12)))
p.append(box(VIDRO, (0, -6.08, 2.2), (1.8, 0.1, 3.2)))
for x in (-1.9, 1.9): p.append(box(VIDRO, (x, -6.08, 3.6), (0.7, 0.1, 1.4)))
# campanário
p.append(box(MADEIRA, (9.5, -2, 3.2), (3, 3, 6.4)))
p.append(mesh_from([(8, -3.5, 6.4), (11, -3.5, 6.4), (11, -0.5, 6.4), (8, -0.5, 6.4), (9.5, -2, 9.2)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], MADEIRA_ESC))
p.append(sphere(DOURADO, (9.5, -2, 9.6), 0.6, (1, 1, 1.3), seg=8, rings=5))
p.append(cyl(0x9a6a2a, (9.5, -2, 5.0), 0.6, 0.9, 8, r2=0.3))
# pêssanka gigante
p.append(sphere(VERMELHO, (-9, 3, 2.4), 1, (1.6, 1.6, 2.2), seg=12, rings=8))
for z, c in ((1.4, AMARELO), (2.4, PRETO), (3.4, AMARELO)):
    p.append(cyl(c, (-9, 3, z), 1.62 * math.sqrt(max(0.05, 1 - ((z - 2.4) / 2.2) ** 2)), 0.25, 12))
asset('memorial_ucraniano', p)

# ---------- Catedral Basílica: neogótica, duas torres com flechas e relógios, rosácea, portal ogival ----------
p = [box(0xe8e2d4, (0, 6, 7.5), (12, 18, 15))]
p.append(mesh_from([(-6.2, -3, 15), (6.2, -3, 15), (6.2, 15, 15), (-6.2, 15, 15), (0, -3, 20), (0, 15, 20)], [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4)], CINZA_ESC))
p.append(mesh_from([(-4.5, -3.05, 15), (4.5, -3.05, 15), (0, -3.05, 19.5)], [(0, 1, 2)], 0xe8e2d4))
for x in (-6.5, 6.5):
    p.append(box(0xe8e2d4, (x, -2.5, 11), (4.2, 4.2, 22)))
    for z in (6, 12, 18): p.append(box(0xd2cab6, (x, -2.5, z), (4.5, 4.5, 0.4)))
    p.append(box(0xe8e2d4, (x, -2.5, 23.0), (3.6, 3.6, 2.0)))
    p.append(mesh_from([(x - 1.9, -4.4, 24), (x + 1.9, -4.4, 24), (x + 1.9, -0.6, 24), (x - 1.9, -0.6, 24), (x, -2.5, 34)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], CINZA_ESC))
    p.append(cyl(DOURADO, (x, -2.5, 34.6), 0.08, 1.4, 4))
    p.append(cyl(BRANCO, (x, -4.66, 19.5), 1.1, 0.12, 16, rot=(math.pi / 2, 0, 0)))
    p.append(box(PRETO, (x, -4.74, 19.8), (0.08, 0.05, 0.8))); p.append(box(PRETO, (x + 0.3, -4.74, 19.5), (0.6, 0.05, 0.08)))
    for dx in (-1.9, 1.9):
        p.append(cyl(0xd2cab6, (x + dx, -4.4, 24.6), 0.25, 1.6, 4, r2=0.02))
    p.append(box(VIDRO, (x, -4.65, 13), (1.0, 0.1, 3.4)))
    p.append(box(VIDRO, (x, -4.65, 7), (1.0, 0.1, 2.6)))
# rosácea e portal ogival
p.append(cyl(VIDRO, (0, -3.05, 11.5), 2.4, 0.2, 16, rot=(math.pi / 2, 0, 0)))
p.append(cyl(0xd2cab6, (0, -3.1, 11.5), 2.8, 0.1, 16, rot=(math.pi / 2, 0, 0)))
for k in range(8):
    a = k / 8 * math.pi; p.append(box(0xd2cab6, (0, -3.2, 11.5), (4.6 * abs(math.cos(a)) + 0.12, 0.05, 4.6 * abs(math.sin(a)) + 0.12)))
p.append(box(MADEIRA_ESC, (0, -3.1, 2.8), (3.2, 0.2, 5.6)))
p.append(mesh_from([(-1.6, -3.12, 5.6), (1.6, -3.12, 5.6), (0, -3.12, 7.6)], [(0, 1, 2)], MADEIRA_ESC))
p.append(box(0xd2cab6, (0, -3.0, 0.4), (14, 1.4, 0.8)))
asset('catedral', p)

# ---------- Paço da Liberdade: casarão eclético com traços art nouveau, esculturas e frontão ornamentado ----------
OCRE_P = 0xe9c27a
p = [box(OCRE_P, (0, 0, 6), (22, 12, 12)), box(BRANCO, (0, 0, 0.6), (22.4, 12.4, 1.2))]
for z in (4.4, 8.4): p.append(box(BRANCO, (0, -6.05, z), (22, 0.15, 0.4)))
p.append(box(BRANCO, (0, 0, 12.3), (22.6, 12.6, 0.6)))
for i in range(11):
    x = -10 + i * 2
    p.append(cyl(BRANCO, (x, -6.2, 12.9), 0.18, 0.6, 6))
p.append(box(BRANCO, (0, -6.2, 13.25), (22, 0.3, 0.12)))
for row, z in enumerate((2.6, 6.4, 10.2)):
    for i in range(8):
        x = -8.75 + i * 2.5
        if abs(x) < 3: continue
        p.append(box(VIDRO, (x, -6.06, z), (1.2, 0.1, 2.2)))
        p += arc_tube(BRANCO, x, -6.12, z + 1.1, 0.62, 0.06, 'y', 0, math.pi, 6, 4)
# corpo central saliente com frontão curvo e brasão
p.append(box(OCRE_P, (0, -6.6, 7), (6, 1.4, 14)))
for z in (2.6, 6.4, 10.2):
    p.append(box(VIDRO, (0, -7.32, z), (2.2, 0.1, 2.6)))
    p += arc_tube(BRANCO, 0, -7.38, z + 1.3, 1.12, 0.07, 'y', 0, math.pi, 8, 4)
p += arc_tube(BRANCO, 0, -7.4, 14.0, 3.0, 0.22, 'y', 0, math.pi, 12, 6)
p.append(cyl(BRANCO, (0, -7.45, 15.2), 1.0, 0.2, 12, rot=(math.pi / 2, 0, 0)))
p.append(cyl(VERMELHO, (0, -7.55, 15.2), 0.6, 0.1, 10, rot=(math.pi / 2, 0, 0)))
for x in (-3.4, 3.4):
    p.append(cyl(BRANCO, (x, -7.4, 14.3), 0.45, 0.6, 8)); p.append(sphere(0xd8d0c0, (x, -7.4, 15.4), 0.6, (1, 1, 1.4), seg=6, rings=5))
p.append(mesh_from([(-11.3, -6.3, 12.6), (11.3, -6.3, 12.6), (11.3, 6.3, 12.6), (-11.3, 6.3, 12.6), (-8, -3, 15), (8, -3, 15), (8, 3, 15), (-8, 3, 15)],
                   [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], 0x4a4f52))
asset('paco_liberdade', p)

# ---------- Teatro Guaíra: concreto modernista em curvas, fachada com o mural de Poty Lazzarotto ----------
p = [box(CONCRETO, (0, 6, 9), (50, 24, 18))]
curve = [(math.sin(a) * 26, -6 - math.cos(a) * 4, 0) for a in [k / 14 * math.pi - math.pi / 2 for k in range(15)]]
p.append(loft([[(x, y, 0.8) for x, y, _ in curve], [(x, y, 16) for x, y, _ in curve]], CONCRETO, cap_bot=False, cap_top=False))
p.append(loft([[(x * 1.03, y - 0.5, 16) for x, y, _ in curve], [(x * 1.03, y - 0.5, 17.6) for x, y, _ in curve]], CONCRETO_ESC, cap_bot=False, cap_top=False))
# brises verticais de concreto
for k in range(1, 14):
    a = k / 14 * math.pi - math.pi / 2; x, y = math.sin(a) * 26.6, -6 - math.cos(a) * 4.6
    p.append(box(CONCRETO_ESC, (x, y, 8.4), (0.5, 1.2, 15.2), rot=(0, 0, a * 0.3)))
# mural de Poty: painel em relevo com figuras geométricas
p.append(box(0xd9d2c0, (0, -10.7, 9.5), (22, 0.3, 9)))
cols = [0x6b6d66, 0x8e8b82, 0xb5582c, 0x3a6fd9, 0x2a2f2c]
for i in range(18):
    x = -9.5 + (i % 6) * 3.8; z = 6.2 + (i // 6) * 2.9
    p.append(box(cols[i % 5], (x + (i % 2) * 0.6, -10.9, z), (1.6 + (i % 3) * 0.5, 0.2, 1.4 + (i % 2) * 0.6), rot=(0, (i % 4 - 1.5) * 0.3, 0)))
# marquise e entrada envidraçada
p.append(box(BRANCO, (0, -13, 4.4), (28, 6, 0.5)))
for x in (-12, -6, 0, 6, 12): p.append(cyl(BRANCO, (x, -15.2, 2.2), 0.35, 4.4, 8))
p.append(box(VIDRO, (0, -10.6, 2.2), (20, 0.2, 4.0)))
p.append(box(CINZA, (0, -14, 0.15), (34, 10, 0.3)))
for i in range(4): p.append(box(CINZA_ESC, (0, -18.6 - i * 0.6, 0.15 + i * 0.0), (30, 0.6, 0.3)))
asset('teatro_guaira', p)

# ---------- Farol do Saber: biblioteca de bairro inspirada no Farol de Alexandria; planta de livro aberto
# (duas alas em V) com a torre cilíndrica de 10 m na lombada ----------
p = []
for s in (-1, 1):
    ang = s * 0.45
    cx, cy = s * 3.6, 1.2
    p.append(box(BRANCO, (cx, cy, 1.7), (6.4, 4.2, 3.4), rot=(0, 0, ang)))
    p.append(box(JEANS, (cx, cy, 3.55), (6.8, 4.6, 0.3), rot=(0, 0, ang)))
    p.append(box(VIDRO, (cx - s * 0.6, cy - 2.12 * math.cos(ang), 1.8), (3.4, 0.1, 1.4), rot=(0, 0, ang)))
p.append(cyl(BRANCO, (0, 0, 4.5), 1.6, 9, 12))
for z in (3.0, 6.0): p.append(cyl(AMARELO, (0, 0, z), 1.65, 0.35, 12))
p.append(cyl(JEANS, (0, 0, 9.2), 2.1, 0.3, 12))
for k in range(8):
    a = k / 8 * math.tau; p.append(box(BRANCO, (math.cos(a) * 2.0, math.sin(a) * 2.0, 9.6), (0.12, 0.12, 0.6)))
p.append(cyl(AGUA, (0, 0, 10.2), 1.2, 1.4, 8))
for k in range(8):
    a = k / 8 * math.tau; p.append(box(BRANCO, (math.cos(a) * 1.22, math.sin(a) * 1.22, 10.2), (0.1, 0.1, 1.4)))
p.append(cyl(VERMELHO, (0, 0, 11.3), 1.4, 0.9, 8, r2=0.15))
p.append(sphere(AMARELO, (0, 0, 11.9), 0.28, seg=6, rings=4))
p.append(box(MADEIRA_ESC, (0, -1.62, 1.2), (1.2, 0.1, 2.4)))
asset('farol_saber', p)

# ---------- Relógio das Flores (Praça Garibaldi): mostrador inclinado de plantas e flores,
# ponteiros mecânicos e marcações coloridas das horas ----------
p = [box(PEDRA, (0, 1.2, 0.35), (10, 6, 0.7))]
tilt = math.radians(32)  # mostrador deitado na encosta, inclinado 32 graus
ct, st_ = math.cos(tilt), math.sin(tilt)
def face(u, v, h=0.0):
    # ponto no mostrador: u para os lados, v subindo pelo mostrador, h para fora (normal)
    return (u, 0.8 + v * ct - h * st_, 1.2 + v * st_ + h * ct)
p.append(cyl(FOLHA, (0, 0.8, 1.2), 4.4, 0.5, 24, rot=(tilt, 0, 0)))
for ring, (R, c) in enumerate([(4.1, VERMELHO), (3.5, AMARELO)]):
    for k in range(24):
        a = k / 24 * math.tau
        p.append(sphere(c if k % 2 else (LILAS if ring else BRANCO), face(math.cos(a) * R, math.sin(a) * R, 0.35), 0.28, seg=5, rings=3))
for k in range(12):
    a = k / 12 * math.tau
    p.append(box(LARANJA if k % 3 == 0 else LILAS, face(math.cos(a) * 2.7, math.sin(a) * 2.7, 0.3), (0.5, 0.5, 0.35)))
p.append(between(BRANCO, face(0, 0, 0.45), face(0, 2.2, 0.45), 0.1, 4))
p.append(between(BRANCO, face(0, 0, 0.5), face(1.5, -0.6, 0.5), 0.12, 4))
p.append(sphere(PRETO, face(0, 0, 0.55), 0.2, seg=6, rings=4))
asset('relogio_flores', p)

# ---------- Estação Curitiba (1885), hoje Shopping Estação: prédio histórico preservado na frente
# e o bloco do shopping de vidro espelhado com a torre do relógio atrás ----------
p = [box(OCRE, (0, 0, 4.6), (34, 10, 9.2)), box(OCRE_ESC, (0, 0, 0.6), (34.4, 10.4, 1.2)), box(BRANCO, (0, 0, 9.4), (34.6, 10.6, 0.5))]
for row, z in enumerate((3.0, 6.9)):
    for i in range(11):
        x = -15 + i * 3
        if abs(x) < 2: continue
        p.append(box(VIDRO, (x, -5.05, z), (1.3, 0.1, 2.1)))
        p += arc_tube(BRANCO, x, -5.1, z + 1.05, 0.68, 0.06, 'y', 0, math.pi, 6, 4)
p.append(box(OCRE, (0, -5.6, 6), (7, 1.6, 12)))
p.append(mesh_from([(-3.8, -6.4, 12), (3.8, -6.4, 12), (0, -6.4, 14.2)], [(0, 1, 2)], BRANCO))
p.append(box(BRANCO, (0, -6.45, 8.6), (5.4, 0.1, 0.5)))
p.append(box(VIDRO, (0, -6.45, 3.6), (3.2, 0.1, 4.8)))
p += arc_tube(BRANCO, 0, -6.5, 6.0, 1.7, 0.1, 'y', 0, math.pi, 8, 4)
p.append(box(BRANCO, (0, -6.5, 10.6), (4.4, 0.1, 0.9)))
# bloco do shopping de vidro espelhado com torre do relógio
p.append(box(0x6f8fa0, (0, 14, 8), (44, 16, 16)))
p += grade(0xd8e0e4, -22, 22, 0.5, 16, 5.95, 22, 5, 0.08)
p.append(box(0x6f8fa0, (0, 7, 18), (6, 6, 20)))
p.append(box(BRANCO, (0, 7, 28.4), (6.6, 6.6, 0.8)))
for s in (-1, 1):
    p.append(cyl(BRANCO, (0, 7 + s * 3.05, 24.5), 2.0, 0.2, 20, rot=(math.pi / 2, 0, 0)))
p.append(box(PRETO, (0, 3.9, 25.1), (0.14, 0.05, 1.3))); p.append(box(PRETO, (0.45, 3.9, 24.5), (0.9, 0.05, 0.14)))
p.append(mesh_from([(-3.3, 3.7, 28.8), (3.3, 3.7, 28.8), (3.3, 10.3, 28.8), (-3.3, 10.3, 28.8), (0, 7, 32)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], TELHA))
p.append(box(FOLHA, (0, -7.2, 1.4), (6, 2.4, 0.2)))
asset('estacao', p)

# ---------- Prédio histórico da UFPR (Praça Santos Andrade): escadaria, colunata e a grande cúpula ----------
p = [box(PEDRA_ESC, (0, 0, 0.5), (34, 18, 1.0))]
for i in range(5): p.append(box(PEDRA, (0, -9.6 - i * 0.5, 0.1 + i * 0.2), (16, 0.5 + i * 0.0, 0.2 + i * 0.4)))
p.append(box(0xf2ede0, (0, 2, 7), (32, 14, 12)))
for i in range(12):
    x = -14.3 + i * 2.6
    if abs(x) < 7: continue
    for z in (4.0, 9.0): p.append(box(VIDRO, (x, -5.05, z), (1.2, 0.1, 2.6)))
p.append(box(0xf2ede0, (0, -6.5, 1.4), (16, 3.6, 0.8)))
for i in range(8): p.append(cyl(BRANCO, (-6.3 + i * 1.8, -7.6, 7.0), 0.45, 10.4, 12))
for i in range(8): p.append(box(PEDRA, (-6.3 + i * 1.8, -7.6, 12.3), (1.1, 1.1, 0.4)))
p.append(box(0xf2ede0, (0, -6.6, 13.0), (16.4, 4.0, 1.2)))
p.append(extrude_xz([(-8.4, 13.6), (8.4, 13.6), (0, 16.4)], -8.6, -4.6, 0xf2ede0))
p.append(box(0xf2ede0, (0, 2, 13.4), (32.4, 14.4, 0.8)))
p.append(cyl(0xf2ede0, (0, 3, 15.6), 5.0, 3.6, 16))
for k in range(16):
    a = k / 16 * math.tau; p.append(cyl(BRANCO, (math.cos(a) * 5.1, 3 + math.sin(a) * 5.1, 15.6), 0.22, 3.6, 6))
p.append(sphere(0x7f9c8a, (0, 3, 17.4), 5.0, (1, 1, 0.85), seg=16, rings=8))
p.append(cyl(0xf2ede0, (0, 3, 22.1), 0.9, 1.4, 8))
p.append(sphere(0x7f9c8a, (0, 3, 23.1), 0.9, seg=8, rings=5))
asset('colunata', p)


# ---------- ônibus da Linha Turismo: dois andares, verde com faixa lima (comprimento no eixo X) ----------
p = [box(FOLHA_ESC, (0, 0, 1.7), (11, 2.6, 2.6), bevel=0.08), box(LIMA, (0, 0, 3.6), (11, 2.6, 1.4), bevel=0.06)]
p.append(box(VIDRO, (0.4, -1.32, 2.0), (9.0, 0.05, 1.1))); p.append(box(VIDRO, (0, -1.32, 3.7), (10.2, 0.05, 0.8)))
p.append(box(VIDRO, (5.52, 0, 2.2), (0.05, 2.2, 1.6))); p.append(box(VIDRO, (5.52, 0, 3.7), (0.05, 2.2, 0.8)))
p.append(box(BRANCO, (0, 0, 4.36), (10.8, 2.5, 0.14)))
p.append(box(AMARELO, (5.53, 0, 0.9), (0.05, 2.0, 0.25)))
p.append(box(BRANCO, (-1.5, -1.33, 1.0), (5.0, 0.04, 0.3)))
for x in (-3.6, 3.6):
    for y in (-1.2, 1.2): p.append(cyl(PRETO, (x, y, 0.5), 0.5, 0.3, 10, rot=(math.pi / 2, 0, 0)))
asset('linha_turismo', p)

# ---------- power-up: guarda-chuva colorido (cabo em J) ----------
p = []
cols = [VERMELHO, AMARELO, LILAS, LIMA, LARANJA, JEANS, VERMELHO, AMARELO]
for k in range(8):
    a0, a1 = k / 8 * math.tau, (k + 1) / 8 * math.tau
    p.append(mesh_from([(0, 0, 1.25), (math.cos(a0) * 1.3, math.sin(a0) * 1.3, 0.55), (math.cos(a1) * 1.3, math.sin(a1) * 1.3, 0.55)], [(0, 1, 2)], cols[k]))
    p.append(mesh_from([(0, 0, 1.2), (math.cos(a1) * 1.28, math.sin(a1) * 1.28, 0.5), (math.cos(a0) * 1.28, math.sin(a0) * 1.28, 0.5)], [(0, 1, 2)], cols[k]))
p.append(cyl(PRETO, (0, 0, 0.3), 0.04, 1.9, 5))
p.append(cyl(PRETO, (0, 0, 1.35), 0.06, 0.2, 5))
p += arc_tube(PRETO, 0.18, 0, -0.62, 0.18, 0.045, 'y', math.pi, 2 * math.pi, 5, 4)
asset('guarda_chuva', p)

# ---------- power-up: Ligeirinho, o ônibus expresso prateado (comprimento no eixo X) ----------
PRATA, PRATA_ESC = 0xc9ccd0, 0x9a9ea4
p = [box(PRATA, (0, 0, 1.75), (12, 2.6, 2.7), bevel=0.12)]
p.append(box(VIDRO, (0.4, -1.32, 2.2), (9.8, 0.06, 1.2)))
p.append(box(VIDRO, (0.4, 1.32, 2.2), (9.8, 0.06, 1.2)))
p.append(box(VIDRO, (6.02, 0, 2.3), (0.06, 2.3, 1.5)))
p.append(box(PRATA_ESC, (0, 0, 3.2), (11.6, 2.4, 0.2)))
p.append(box(VERMELHO, (0, -1.34, 1.05), (11.8, 0.04, 0.22)))
p.append(box(BRANCO, (6.04, 0, 3.0), (0.05, 1.6, 0.35)))
for y in (-0.9, 0.9): p.append(box(AMARELO, (6.04, y, 1.0), (0.05, 0.35, 0.2)))
for x in (-3.8, 3.8):
    for y in (-1.25, 1.25): p.append(cyl(PRETO, (x, y, 0.55), 0.55, 0.3, 10, rot=(math.pi / 2, 0, 0)))
asset('ligeirinho', p)

# ================= abertura: parque de diversões do Barigui alagado =================
ROSA = 0xe05a9a

# roda-gigante: base (pernas em A, plataforma e escada); eixo do giro a 14 m de altura
p = []
for sy in (-2.4, 2.4):
    for sx in (-6.5, 6.5): p.append(between(BRANCO, (sx, sy, 0), (0, sy * 0.45, 14), 0.32, 8))
    p.append(between(BRANCO, (-4.2, sy, 4.5), (4.2, sy, 4.5), 0.16, 6))
    p.append(between(BRANCO, (-2.6, sy * 0.7, 9.0), (2.6, sy * 0.7, 9.0), 0.14, 6))
p.append(box(CINZA, (0, 0, 0.4), (16, 7, 0.8)))
p.append(box(LIMA, (0, -4.2, 1.4), (5, 1.6, 0.2)))
for k in range(5): p.append(box(CINZA_ESC, (0, -5.2 - k * 0.5, 0.2 + k * 0.25), (3, 0.5, 0.15)))
p.append(cyl(CINZA_ESC, (0, 0, 14), 0.5, 6.2, 10, rot=(math.pi / 2, 0, 0)))
asset('rg_base', p)

# roda-gigante: a roda (gira no eixo Y do Blender; origem no cubo)
p = []
for sy in (-1.1, 1.1):
    prim('torus', BRANCO, (0, sy, 0), (math.pi / 2, 0, 0), major_radius=12, minor_radius=0.14, major_segments=32, minor_segments=4); p.append(bpy.context.active_object)
    prim('torus', BRANCO, (0, sy, 0), (math.pi / 2, 0, 0), major_radius=9.6, minor_radius=0.09, major_segments=28, minor_segments=4); p.append(bpy.context.active_object)
    for k in range(16):
        a = k / 16 * math.tau
        p.append(between(BRANCO, (0, sy, 0), (math.cos(a) * 12, sy, math.sin(a) * 12), 0.07, 4))
        a2 = (k + 0.5) / 16 * math.tau
        p.append(between(BRANCO, (math.cos(a) * 9.6, sy, math.sin(a) * 9.6), (math.cos(a2) * 12, sy, math.sin(a2) * 12), 0.05, 4))
for k in range(16):
    a = k / 16 * math.tau
    p.append(between(BRANCO, (math.cos(a) * 12, -1.1, math.sin(a) * 12), (math.cos(a) * 12, 1.1, math.sin(a) * 12), 0.06, 4))
p.append(cyl(CINZA, (0, 0, 0), 1.3, 2.6, 16, rot=(math.pi / 2, 0, 0)))
p.append(cyl(BRANCO, (0, -1.35, 0), 1.0, 0.1, 16, rot=(math.pi / 2, 0, 0)))
asset('rg_roda', p)

# gôndola: pendurada no ponto de giro (origem); o jogo tinge por instância
p = [box(0xeeeeee, (0, 0, -0.35), (1.9, 1.9, 0.25), bevel=0.05)]
for sx in (-0.85, 0.85):
    for sy in (-0.85, 0.85): p.append(cyl(0xcfcfcf, (sx, sy, -1.2), 0.05, 1.6, 4))
p.append(box(0xdedede, (0, 0, -1.95), (1.9, 1.9, 0.7)))
p.append(box(0x9fd3e0, (0, 0, -1.25), (1.7, 1.7, 0.9)))
p.append(cyl(0xcfcfcf, (0, 0, -0.1), 0.06, 0.4, 4))
asset('rg_gondola', p)

# kamikaze (pêndulo): base de pernas brancas, eixo a 20 m
p = [box(CINZA, (0, 0, 0.3), (18, 12, 0.6))]
for sy in (-3.2, 3.2):
    for sx in (-7.5, 7.5): p.append(between(BRANCO, (sx, sy * 1.7, 0.6), (0, sy, 20), 0.42, 8))
    p.append(between(BRANCO, (-4.5, sy * 1.35, 9), (4.5, sy * 1.35, 9), 0.18, 6))
p.append(cyl(CINZA_ESC, (0, 0, 20), 0.7, 7.4, 10, rot=(math.pi / 2, 0, 0)))
asset('pend_base', p)

# kamikaze: braço que balança (origem no eixo; azul em cima, amarelo, rosa e o anel de assentos vermelhos embaixo)
p = [box(BRANCO, (0, 0, 2.4), (1.6, 1.6, 2.4), bevel=0.08), box(0xfff2c4, (0, -0.82, 2.6), (1.2, 0.05, 1.6))]
p.append(cyl(JEANS, (0, 0, -3), 0.75, 6, 10))
p.append(cyl(AMARELO, (0, 0, -8.5), 0.75, 5, 10))
p.append(cyl(ROSA, (0, 0, -12.5), 0.85, 3, 10))
p.append(cyl(CINZA_ESC, (0, 0, -14.4), 4.2, 0.4, 20))
for k in range(16):
    a = k / 16 * math.tau
    p.append(box(VERMELHO, (math.cos(a) * 3.6, math.sin(a) * 3.6, -15.0), (0.9, 0.7, 0.9), rot=(0, 0, a), bevel=0.05))
    p.append(between(ROSA, (0, 0, -14.2), (math.cos(a) * 4.0, math.sin(a) * 4.0, -14.6), 0.06, 4))
p.append(cyl(ROSA, (0, 0, -15.6), 1.2, 1.0, 12, r2=0.3))
asset('pend_braco', p)

# portal do parque: duas torres de castelo com telhado cônico e a faixa da entrada
p = []
for sx in (-4.6, 4.6):
    for k in range(5): p.append(cyl(LARANJA if k % 2 == 0 else AMARELO, (sx, 0, 0.6 + k * 1.2), 1.3, 1.2, 10))
    p.append(cyl(LILAS, (sx, 0, 6.8), 1.55, 0.4, 10))
    p.append(cyl(LILAS, (sx, 0, 8.4), 1.6, 2.8, 10, r2=0.05))
    p.append(cyl(AMARELO, (sx, 0, 9.9), 0.05, 0.6, 4))
    p.append(box(VERMELHO, (sx + 0.25, 0, 10.1), (0.5, 0.04, 0.3)))
p.append(box(LARANJA, (0, 0, 5.6), (8.2, 0.4, 1.6), bevel=0.06))
p.append(box(AMARELO, (0, -0.22, 5.6), (7.8, 0.05, 1.3)))
for k in range(6): p.append(box([VERMELHO, JEANS, LIMA][k % 3], (-3.2 + k * 1.28, -0.26, 5.6), (0.8, 0.04, 0.6)))
asset('portal_parque', p)

# bilheteria: quiosque onde a capivara espera a água subir (telhado plano a 3 m)
p = [box(AMARELO, (0, 0, 1.4), (3.2, 3.2, 2.8)), box(VERMELHO, (0, 0, 2.95), (3.8, 3.8, 0.3), bevel=0.05)]
p.append(box(JEANS, (0, 0, 2.75), (3.3, 3.3, 0.2)))
p.append(box(VIDRO, (0, -1.62, 1.6), (1.8, 0.06, 1.0)))
for k in range(5): p.append(box([LIMA, ROSA, LARANJA][k % 3], (-1.2 + k * 0.6, -1.64, 0.7), (0.5, 0.04, 0.5)))
asset('bilheteria', p)

# barraca de doces com toldo listrado
p = [box(BRANCO, (0, 0, 1.0), (3, 2.4, 2.0))]
for k in range(8):
    a0, a1 = k / 8 * math.tau, (k + 1) / 8 * math.tau
    p.append(mesh_from([(0, 0, 4.0), (math.cos(a0) * 2.4, math.sin(a0) * 2.4, 2.4), (math.cos(a1) * 2.4, math.sin(a1) * 2.4, 2.4)], [(0, 1, 2)], VERMELHO if k % 2 else BRANCO))
p.append(sphere(AMARELO, (0, 0, 4.1), 0.2, seg=6, rings=4))
asset('barraca', p)

# palmeira
p = []
pts_ = [(0, 0, 0), (0.3, 0, 2.5), (0.8, 0, 5), (1.2, 0, 7.2)]
for a, b in zip(pts_, pts_[1:]): p.append(between(MADEIRA, a, b, 0.32, 7, r2=0.26))
top = pts_[-1]
for k in range(8):
    a = k / 8 * math.tau
    tip = (top[0] + math.cos(a) * 3.2, top[1] + math.sin(a) * 3.2, top[2] - 1.4)
    mid = (top[0] + math.cos(a) * 1.8, top[1] + math.sin(a) * 1.8, top[2] + 0.4)
    p.append(between(FOLHA if k % 2 else FOLHA_ESC, top, mid, 0.35, 4, r2=0.3))
    p.append(between(FOLHA if k % 2 else FOLHA_ESC, mid, tip, 0.3, 4, r2=0.05))
asset('palmeira', p)

# cerca branca (4 m no eixo X)
p = [box(BRANCO, (0, 0, 0.55), (4, 0.08, 0.1)), box(BRANCO, (0, 0, 0.95), (4, 0.08, 0.1))]
for k in range(9): p.append(box(BRANCO, (-1.8 + k * 0.45, 0, 0.6), (0.18, 0.06, 1.2)))
asset('cerca', p)

# cacho de balões
p = []
for k, (c, x, y, z) in enumerate([(VERMELHO, 0, 0, 3.2), (AMARELO, 0.6, 0.2, 3.6), (JEANS, -0.5, 0.3, 3.7), (LIMA, 0.2, -0.5, 4.1), (ROSA, -0.3, -0.3, 3.0)]):
    p.append(sphere(c, (x, y, z), 0.45, (1, 1, 1.2), seg=8, rings=6))
    p.append(between(0xdddddd, (0, 0, 0.2), (x, y, z - 0.5), 0.015, 3))
asset('baloes', p)

# capivara heroína em pé (com colete lima e a laranja na cabeça), frente +Y
p = [sphere(CAPI, (0, 0, 0.8), 1, (0.45, 0.8, 0.45), seg=10, rings=7)]
p.append(cyl(LIMA, (0, 0.05, 0.85), 0.5, 0.75, 10, rot=(math.pi / 2, 0, 0)))
p.append(box(LARANJA, (0, 0.05, 1.36), (0.2, 0.7, 0.05)))
p.append(box(CAPI, (0, 0.82, 1.12), (0.44, 0.64, 0.44), rot=(0.25, 0, 0), bevel=0.08))
p.append(box(CAPI_ESC, (0, 1.12, 1.02), (0.36, 0.1, 0.27), bevel=0.04))
for s_ in (-1, 1):
    p.append(sphere(PRETO, (s_ * 0.21, 0.96, 1.24), 0.05, seg=6, rings=4))
    p.append(sphere(CAPI_ESC, (s_ * 0.16, 0.58, 1.38), 0.07, (1, 0.6, 1), seg=6, rings=4))
    for y in (-0.42, 0.42): p.append(cyl(CAPI_ESC, (s_ * 0.23, y, 0.27), 0.1, 0.54, 6))
p.append(sphere(LARANJA, (0, 0.76, 1.47), 0.14, seg=8, rings=6))
p.append(box(FOLHA_ESC, (0.05, 0.76, 1.63), (0.14, 0.05, 0.03), rot=(0, 0.5, 0)))
asset('capivara_heroi', p)

# ---------------- material de cor por vértice (para o preview e o exportador) ----------------
# ---------------- equipe da poda: dois trabalhadores de colete e capacete cortando uma árvore caída ----------------
PELE, REFLEX = 0xc98a5e, 0xe8eadf
def pessoa(ox, oy, yaw, tool):
    c, s_ = math.cos(yaw), math.sin(yaw)
    P = lambda x, y, z: (ox + x * c - y * s_, oy + x * s_ + y * c, z)
    R = (0, 0, yaw)
    q = []
    for sx in (-1, 1): q.append(box(JEANS, P(sx * 0.12, 0, 0.45), (0.18, 0.22, 0.9), R))
    q.append(box(0x2f5fb0, P(0, 0, 1.2), (0.46, 0.26, 0.62), R))          # camisa
    q.append(box(LARANJA, P(0, 0, 1.22), (0.5, 0.3, 0.56), R))           # colete
    for z in (1.08, 1.32): q.append(box(REFLEX, P(0, 0, z), (0.52, 0.32, 0.06), R))  # faixas refletivas
    q.append(sphere(PELE, P(0, 0, 1.68), 0.15, seg=8, rings=6))
    q.append(sphere(AMARELO, P(0, 0, 1.76), 0.18, (1, 1, 0.75), seg=8, rings=5))   # capacete
    q.append(cyl(AMARELO, P(0, 0.04, 1.73), 0.22, 0.03, 10))
    sh = [P(sx * 0.3, 0, 1.45) for sx in (-1, 1)]
    if tool == 'serra':
        hands = [P(-0.12, 0.42, 1.05), P(0.12, 0.42, 1.05)]
        q.append(box(LARANJA, P(0, 0.48, 1.0), (0.2, 0.42, 0.22), R))       # motosserra
        q.append(box(PRETO, P(0, 0.5, 1.13), (0.06, 0.3, 0.06), R))
        q.append(box(CINZA, P(0, 0.98, 0.96), (0.05, 0.66, 0.08), R))       # sabre
    else:
        hands = [P(-0.15, 0.35, 1.15), P(0.15, 0.3, 1.25)]
        q.append(between(MADEIRA, P(0.15, -0.2, 1.7), P(0.15, 0.9, 0.05), 0.03, 5))  # rastelo
        q.append(box(CINZA_ESC, P(0.15, 0.95, 0.04), (0.5, 0.06, 0.06), R))
    for a, b in zip(sh, hands): q.append(between(0x2f5fb0, a, b, 0.07, 5))
    for h in hands: q.append(sphere(PELE, h, 0.06, seg=6, rings=4))
    return q
p = []
p.append(cyl(MADEIRA, (0, 1.2, 0.35), 0.34, 0.7, 7))                     # toco
p.append(cyl(0xd9b98a, (0, 1.2, 0.71), 0.3, 0.02, 7))
p.append(between(MADEIRA, (0.4, 1.3, 0.35), (6.2, 1.9, 0.6), 0.3, 7, r2=0.2))  # tronco caído
for (x, y, z, r, col) in [(6.6, 2.0, 1.1, 1.9, FOLHA), (5.2, 2.6, 0.9, 1.4, FOLHA_ESC), (7.4, 1.2, 0.8, 1.3, FOLHA_ESC), (4.6, 1.2, 0.7, 1.0, FOLHA)]:
    p.append(ico(col, (x, y, z), r, (1, 1, 0.7)))
for (x, y) in [(2.2, 1.0), (3.4, 1.2)]: p.append(cyl(0xd9b98a, (x, y, 0.36), 0.25, 0.5, 7, rot=(0, math.pi / 2, 0.1)))  # toras cortadas
p += pessoa(1.5, 0.95, -math.pi / 2, 'serra')       # de perfil para a rua, serrando as toras
p += pessoa(-1.1, 0.7, -1.1, 'rastelo')
for x in (-2.6, 3.0, 5.4):
    p.append(cyl(LARANJA, (x, -0.6, 0.38), 0.22, 0.76, 8, r2=0.03))
    p.append(cyl(BRANCO, (x, -0.6, 0.45), 0.15, 0.12, 8))
    p.append(box(LARANJA, (x, -0.6, 0.03), (0.5, 0.5, 0.06)))
asset('equipe_poda', p)

# ---------------- loja: chapéus (origem = topo da cabeça da capivara no jet ski; frente +Y) ----------------
p = [sphere(0xc23b3b, (0, 0, 0.08), 0.24, (1, 1.05, 0.75), seg=10, rings=6)]            # touca de lã com pompom
p.append(cyl(0xf4f4ec, (0, 0, 0.0), 0.25, 0.1, 10))
p.append(sphere(0xf4f4ec, (0, 0, 0.27), 0.08, seg=6, rings=4))
asset('chapeu_touca', p)
p = [sphere(AMARELO, (0, 0, 0.05), 0.25, (1, 1.1, 0.72), seg=10, rings=6), cyl(AMARELO, (0, 0.03, -0.02), 0.31, 0.04, 12)]  # capacete de obra
p.append(box(0xe0a820, (0, 0, 0.2), (0.06, 0.4, 0.06)))
asset('chapeu_capacete', p)
p = [sphere(JEANS, (0, -0.02, 0.04), 0.23, (1, 1.05, 0.7), seg=10, rings=6), box(JEANS, (0, 0.27, -0.02), (0.34, 0.3, 0.035), rot=(0.12, 0, 0))]  # boné
p.append(sphere(BRANCO, (0, -0.02, 0.2), 0.04, seg=6, rings=4))
asset('chapeu_bone', p)
p = [cyl(0xe7c77a, (0, 0, -0.01), 0.42, 0.04, 14), cyl(0xe7c77a, (0, 0, 0.12), 0.2, 0.26, 12, r2=0.17), cyl(VERMELHO, (0, 0, 0.04), 0.205, 0.06, 12)]  # chapéu de palha
asset('chapeu_palha', p)
p = [cyl(0xf2c230, (0, 0, 0.07), 0.22, 0.14, 10)]                                       # coroa
for k in range(5):
    a = k / 5 * math.tau
    p.append(cyl(0xf2c230, (math.cos(a) * 0.19, math.sin(a) * 0.19, 0.2), 0.06, 0.16, 4, r2=0.0))
    p.append(sphere([VERMELHO, JEANS, LIMA][k % 3], (math.cos(a) * 0.22, math.sin(a) * 0.22, 0.08), 0.035, seg=6, rings=4))
asset('chapeu_coroa', p)

# ---------------- moradores boiando numa boia, acenando (frente +Y) ----------------
for nome, boia, camisa in [('pessoa_boia', VERMELHO, JEANS), ('pessoa_boia2', AMARELO, ROSA)]:
    p = [prim('torus', boia, (0, 0, 0.12), major_radius=0.55, minor_radius=0.2, major_segments=12, minor_segments=6)]
    for k in range(4):
        a = k / 4 * math.tau + 0.4
        p.append(box(BRANCO, (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.14), (0.14, 0.14, 0.42), rot=(0, 0, a)))
    p.append(box(camisa, (0, 0, 0.45), (0.42, 0.26, 0.5)))
    p.append(sphere(PELE, (0, 0, 0.86), 0.16, seg=8, rings=6))
    p.append(sphere(0x3a2618, (0, -0.03, 0.93), 0.155, (1, 1, 0.7), seg=8, rings=5))
    p.append(between(camisa, (-0.24, 0, 0.62), (-0.5, 0.05, 1.15), 0.06, 5))      # braço acenando
    p.append(sphere(PELE, (-0.52, 0.05, 1.2), 0.06, seg=6, rings=4))
    p.append(between(camisa, (0.24, 0, 0.62), (0.45, 0.1, 0.3), 0.06, 5))
    asset(nome, p)

mat = bpy.data.materials.new('VC'); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes.get('Principled BSDF')
attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 0.8
for o in ASSETS.values():
    o.data.materials.clear(); o.data.materials.append(mat)
    o.data.color_attributes.active_color = o.data.color_attributes['Col']

tris = {n: sum(len(p.vertices) - 2 for p in o.data.polygons) for n, o in ASSETS.items()}
print('TRIS', tris, 'total', sum(tris.values()))

os.makedirs(OUT, exist_ok=True)
glb = os.path.join(OUT, 'assets.glb')
kw = dict(filepath=glb, export_format='GLB', use_selection=False, export_apply=True, export_yup=True, export_materials='EXPORT')
try:
    bpy.ops.export_scene.gltf(**kw, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(**kw)
# o host do artifact serve .json, mas não .glb: vira glTF com o buffer embutido em base64
import json, struct, base64
raw = open(glb, 'rb').read()
jlen = struct.unpack_from('<I', raw, 12)[0]
gj = json.loads(raw[20:20 + jlen])
blen = struct.unpack_from('<I', raw, 20 + jlen)[0]
gj['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(raw[28 + jlen:28 + jlen + blen]).decode()
final = os.path.join(OUT, 'assets.json')
json.dump(gj, open(final, 'w'), separators=(',', ':'))
os.remove(glb)
print('GLTF', final, os.path.getsize(final))

# ---------------- preview (Workbench, cor por vértice) ----------------
def render(path, names, spacing, cam_loc, cam_rot, ortho, target=None):
    for o in ASSETS.values(): o.hide_render = o.name not in names
    x = 0
    for n in names:
        o = ASSETS[n]; o.location = (x, 0, 0); x += spacing.get(n, 4)
    cx = (x - spacing.get(names[-1], 4)) / 2
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in bpy.context.scene.objects: bpy.context.scene.collection.objects.link(cam)
    cam.location = (cx + cam_loc[0], cam_loc[1], cam_loc[2]); cam.rotation_euler = cam_rot
    cam.constraints.clear()
    if target:
        tg = bpy.data.objects.get('tg') or bpy.data.objects.new('tg', None)
        if tg.name not in bpy.context.scene.objects: bpy.context.scene.collection.objects.link(tg)
        tg.location = target; c = cam.constraints.new('TRACK_TO'); c.target = tg; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    sc = bpy.context.scene; sc.camera = cam
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_shadows = True; sh.show_cavity = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.film_transparent = False
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    sh.background_type = 'VIEWPORT'; sh.background_color = (0.89, 0.93, 0.82)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

if '--preview' in sys.argv:
    render(os.path.join(OUT, 'preview_piloto.png'), ['jetski', 'capivara'], {'jetski': 0, 'capivara': 0}, (4.5, 5.5, 3.2), (0, 0, 0), 4.6, target=(0, 0.1, 1.1))
    render(os.path.join(OUT, 'preview_poda.png'), ['chapeu_touca', 'chapeu_capacete', 'chapeu_bone', 'chapeu_palha', 'chapeu_coroa', 'pessoa_boia', 'pessoa_boia2'], {'chapeu_touca': 1.2, 'chapeu_capacete': 1.2, 'chapeu_bone': 1.2, 'chapeu_palha': 1.3, 'chapeu_coroa': 1.5, 'pessoa_boia': 1.8, 'pessoa_boia2': 1.8}, (0, -8, 3), (math.radians(70), 0, 0), 9, target=(4.3, 0, 0.4))
    render(os.path.join(OUT, 'preview_parque.png'), ['capivara_heroi', 'baloes', 'cerca', 'barraca', 'bilheteria', 'palmeira', 'portal_parque', 'rg_base', 'pend_base'], {'capivara_heroi': 4, 'baloes': 4, 'cerca': 6, 'barraca': 7, 'bilheteria': 8, 'palmeira': 10, 'portal_parque': 18, 'rg_base': 22, 'pend_base': 4}, (0, -110, 14), (math.radians(82), 0, 0), 105)
    render(os.path.join(OUT, 'preview_bi.png'), ['bi_frente', 'bi_meio', 'bi_tras'], {'bi_frente': 3.1, 'bi_meio': 3.1, 'bi_tras': 3.1}, (-12, -14, 5), (0, 0, 0), 16, target=(3.1, 0, 0))
    render(os.path.join(OUT, 'preview_v2_a.png'), ['relogio_flores', 'farol_saber', 'memorial_ucraniano', 'rua_24h', 'paco_liberdade', 'catedral'], {'relogio_flores': 14, 'farol_saber': 16, 'memorial_ucraniano': 26, 'rua_24h': 34, 'paco_liberdade': 30, 'catedral': 4}, (0, -130, 22), (math.radians(80), 0, 0), 150)
    render(os.path.join(OUT, 'preview_v2_b.png'), ['jardim_botanico', 'opera_arame', 'museu_olho', 'torre_panoramica'], {'jardim_botanico': 34, 'opera_arame': 40, 'museu_olho': 40, 'torre_panoramica': 4}, (0, -150, 30), (math.radians(78), 0, 0), 150)
    render(os.path.join(OUT, 'preview_v2_c.png'), ['estacao', 'colunata', 'teatro_guaira'], {'estacao': 52, 'colunata': 54, 'teatro_guaira': 4}, (0, -150, 26), (math.radians(80), 0, 0), 170)
    render(os.path.join(OUT, 'preview_icones.png'), ['relogio_flores', 'linha_turismo', 'memorial_ucraniano', 'rua_24h', 'opera_arame', 'jardim_botanico', 'paco_liberdade', 'catedral', 'museu_olho', 'torre_panoramica'],
           {'relogio_flores': 12, 'linha_turismo': 15, 'memorial_ucraniano': 14, 'rua_24h': 20, 'opera_arame': 24, 'jardim_botanico': 25, 'paco_liberdade': 22, 'catedral': 24, 'museu_olho': 26, 'torre_panoramica': 4}, (0, -170, 20), (math.radians(84), 0, 0), 210)
    render(os.path.join(OUT, 'preview_marcos.png'), ['pinhao', 'bondinho', 'locomotiva', 'farol_saber', 'memorial_arabe', 'portao_passeio', 'ruinas', 'estacao', 'teatro_guaira', 'onda'],
           {'pinhao': 6, 'bondinho': 12, 'locomotiva': 14, 'farol_saber': 13, 'memorial_arabe': 20, 'portao_passeio': 24, 'ruinas': 34, 'estacao': 50, 'teatro_guaira': 50, 'onda': 4}, (0, -150, 20), (math.radians(82), 0, 0), 230)
    render(os.path.join(OUT, 'preview_pinhao.png'), ['pinhao'], {'pinhao': 0}, (2.2, -3.2, 1.2), (0, 0, 0), 3.2, target=(0, 0, 0))
    render(os.path.join(OUT, 'preview_cenario.png'), ['pato', 'boia', 'banco', 'lixeiras', 'placa', 'tapume', 'capivara_enfeite', 'canoa', 'banca', 'luminaria', 'chafariz', 'obelisco', 'colunata', 'portal'],
           {'pato': 2, 'boia': 2.5, 'banco': 3.5, 'lixeiras': 3.5, 'placa': 3.5, 'tapume': 4.5, 'capivara_enfeite': 3, 'canoa': 3, 'banca': 4.5, 'luminaria': 6, 'chafariz': 8, 'obelisco': 7, 'colunata': 17, 'portal': 10}, (0, -70, 8), (math.radians(84), 0, 0), 80)
    render(os.path.join(OUT, 'preview_props.png'), ['equipe_poda', 'pinhao', 'lixo', 'cone', 'fusivel', 'galho', 'poste', 'arvore_verde', 'ipe_amarelo', 'ipe_roxo', 'araucaria', 'bi_frente', 'tubo', 'lancha_copel'],
           {'equipe_poda': 12, 'pinhao': 2.5, 'lixo': 2.5, 'cone': 3, 'fusivel': 6, 'galho': 8, 'poste': 7, 'arvore_verde': 8, 'ipe_amarelo': 8, 'ipe_roxo': 9, 'araucaria': 10, 'bi_frente': 7, 'tubo': 8, 'lancha_copel': 4},
           (0, -60, 14), (math.radians(80), 0, 0), 90)
