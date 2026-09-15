"""
02_build_blender.py — Fiche 005 : rendu isométrique de MicroMacro-Castres.

Construit la scène 3D à partir de data/blocks.json (fiche 004, unités
« case » : 1 case = 1 unité, 1 niveau = 1 unité), règle une caméra
isométrique et Freestyle en ligne claire (noir sur blanc, sans ombre),
puis rend un PNG.

Usage (bpy installé comme module Python, ou Blender en ligne de commande) :
  python3 pipeline/02_build_blender.py data/blocks.json out/ [largeur_px] [orientation] [inclinaison] [feuille]
  blender -b -P pipeline/02_build_blender.py -- data/blocks.json out/ 6000 45

Sorties : out/castres.png, out/castres.blend (et out/castres.svg si l'add-on
d'export SVG Freestyle est disponible).
"""

import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

# ---------------------------------------------------------------------------
# Paramètres visuels (unités : case ; 1 case ≈ 5,9 m, 1 niveau = 1 case)
# ---------------------------------------------------------------------------
LEVEL_H = 1.0
WIN_OFFSET = 0.02          # les fenêtres flottent devant la façade
MIN_WALL_FOR_WINDOW = 0.6  # mur plus court : pas de fenêtre
WIN_PITCH = 0.75           # entre deux fenêtres
GABLE_H = 0.7              # hauteur du faîtage au-dessus du mur
PARAPET_H = 0.22           # garde-corps des terrasses
PARAPET_T = 0.08
TREE_TRUNK_H = 0.55
LINE_THICKNESS = 1.4       # px : épaisseur du trait Freestyle
ISO_TILT = 54.7356         # ° : vraie isométrie (30° sur le papier)
ISO_TURN = 45.0            # ° : orientation de la carte ; essayer 45 / 135 / 225 / 315
MAX_Z = 8.0                # hauteur max de la scène (clocher 6 + marge) pour le cadrage

MOTIF = {   # (largeur, hauteur, hauteur d'allège) des fenêtres d'étage
    "carre": (0.32, 0.32, 0.36),
    "haute": (0.26, 0.5, 0.28),
    "vitrine": (0.26, 0.5, 0.28),   # étages ; le rez-de-chaussée est traité à part
    "arcade": (0.26, 0.5, 0.28),
}
WAVE_L, WAVE_H = 0.45, 0.06   # vaguelettes de l'Agout (longueur, hauteur)
GROUND_Z = {"water": 0.01, "park": 0.01, "road": 0.02, "place": 0.03, "sidewalk": 0.04}


# ---------------------------------------------------------------------------
# Utilitaires scène
# ---------------------------------------------------------------------------
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def white_material():
    m = bpy.data.materials.new("Blanc")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def new_object(name, bm, mat, collection):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    collection.objects.link(ob)
    return ob


def rings_of(geom):
    """Anneaux (extérieur + trous) d'un Polygon GeoJSON, sans le point de fermeture."""
    rings = []
    for ring in geom["coordinates"]:
        pts = [(float(x), float(y)) for x, y in ring]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) >= 3:
            rings.append(pts)
    return rings


def add_flat_polygon(bm, rings, z):
    """Face plane (avec trous) à la hauteur z. Retourne les BMVerts créés par anneau."""
    loops = [[Vector((x, y, z)) for x, y in r] for r in rings]
    verts_by_ring = [[bm.verts.new(v) for v in loop] for loop in loops]
    flat = [v for ring in verts_by_ring for v in ring]
    for tri in tessellate_polygon(loops):
        try:
            bm.faces.new([flat[i] for i in tri])
        except ValueError:
            pass
    return verts_by_ring


# ---------------------------------------------------------------------------
# Bâtiments
# ---------------------------------------------------------------------------
def build_volume(bm, rings, h, roof, z0=0.0):
    """Murs + toit entre z0 et z0 + h. Retourne la liste des murs [(a, b, h)] pour les fenêtres."""
    walls = []
    ext = rings[0]
    n = len(ext)
    gable = (roof == "pignon" and n == 4 and len(rings) == 1)

    bottom = add_flat_polygon(bm, rings, z0)
    top = [[bm.verts.new(Vector((v.co.x, v.co.y, z0 + h))) for v in ring] for ring in bottom]

    # murs
    for rb, rt in zip(bottom, top):
        m = len(rb)
        for i in range(m):
            a, b = rb[i], rb[(i + 1) % m]
            at, bt = rt[i], rt[(i + 1) % m]
            try:
                bm.faces.new([a, b, bt, at])
            except ValueError:
                pass
            walls.append(((a.co.x, a.co.y), (b.co.x, b.co.y), h))

    if not gable:
        t = top[0]
        flat = [v for ring in top for v in ring]
        loops = [[v.co for v in ring] for ring in top]
        for tri in tessellate_polygon(loops):
            try:
                bm.faces.new([flat[i] for i in tri])
            except ValueError:
                pass
        return walls

    # toit à deux pans : faîtage parallèle au grand côté
    p = top[0]
    d01 = (p[1].co - p[0].co).length
    d12 = (p[2].co - p[1].co).length
    if d01 >= d12:
        sa, sb = (1, 2), (3, 0)     # petits côtés
        ra, rb_ = (0, 1), (2, 3)    # grands côtés
    else:
        sa, sb = (0, 1), (2, 3)
        ra, rb_ = (1, 2), (3, 0)
    ridge_h = min(GABLE_H, 0.55 * min(d01, d12))
    ma = bm.verts.new((p[sa[0]].co + p[sa[1]].co) / 2 + Vector((0, 0, ridge_h)))
    mb = bm.verts.new((p[sb[0]].co + p[sb[1]].co) / 2 + Vector((0, 0, ridge_h)))
    for f in ([p[sa[0]], p[sa[1]], ma], [p[sb[0]], p[sb[1]], mb],
              [p[ra[0]], p[ra[1]], ma, mb], [p[rb_[0]], p[rb_[1]], mb, ma]):
        try:
            bm.faces.new(f)
        except ValueError:
            pass
    return walls


def add_parapet(bm, rings, h):
    """Garde-corps d'une terrasse : anneau mince posé sur le toit plat."""
    ext = rings[0]
    n = len(ext)
    if n != 4:
        return
    xs, ys = [p[0] for p in ext], [p[1] for p in ext]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    t = PARAPET_T
    if x1 - x0 < 4 * t or y1 - y0 < 4 * t:
        return
    outer = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    inner = [(x0 + t, y0 + t), (x0 + t, y1 - t), (x1 - t, y1 - t), (x1 - t, y0 + t)]  # sens inverse = trou
    build_volume(bm, [outer, inner], PARAPET_H, "plat", z0=h)


def arch_points(w, h, segs=7):
    """Contour d'une arcade (rectangle + plein cintre) en coordonnées (u, v)."""
    r = w / 2.0
    pts = [(-r, 0.0), (r, 0.0), (r, h - r)]
    for i in range(1, segs):
        a = math.pi * i / segs
        pts.append((r * math.cos(a), h - r + r * math.sin(a)))
    pts.append((-r, h - r))
    return pts


def add_windows(bm, walls, levels, motif):
    if motif == "none" or not walls:
        return
    ww, wh, sill = MOTIF.get(motif, MOTIF["carre"])
    for (ax, ay), (bx, by), h in walls:
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        if L < MIN_WALL_FOR_WINDOW:
            continue
        ux, uy = dx / L, dy / L            # le long du mur
        nx, ny = uy, -ux                   # vers l'extérieur (anneau anti-horaire)
        ox, oy = ax + nx * WIN_OFFSET, ay + ny * WIN_OFFSET

        def quad(u0, v0, w_, h_):
            pts = [(u0, v0), (u0 + w_, v0), (u0 + w_, v0 + h_), (u0, v0 + h_)]
            place(pts)

        def place(uv):
            vs = [bm.verts.new(Vector((ox + ux * u, oy + uy * u, v))) for u, v in uv]
            try:
                bm.faces.new(vs)
            except ValueError:
                pass

        for lvl in range(levels):
            z0 = lvl * LEVEL_H
            if lvl == 0 and motif == "vitrine":
                # vitrines séparées par des trumeaux, une par ~1 case
                cols = max(1, int((L - 0.25) // 1.0))
                vw = (L - 0.25 * (cols + 1)) / cols
                for c in range(cols):
                    quad(0.25 + c * (vw + 0.25), z0 + 0.08, vw, 0.72)
                continue
            if lvl == 0 and motif == "arcade":
                aw, ah = 0.5, 0.8
                cols = max(1, int((L - 0.25) // (aw + 0.28)))
                gap = (L - cols * aw) / (cols + 1)
                for c in range(cols):
                    u0 = gap + c * (aw + gap) + aw / 2
                    place([(u0 + u, z0 + v) for u, v in arch_points(aw, ah)])
                continue
            cols = max(1, int((L - 0.25) // WIN_PITCH))
            gap = (L - cols * ww) / (cols + 1)
            for c in range(cols):
                quad(gap + c * (ww + gap), z0 + sill, ww, wh)


# ---------------------------------------------------------------------------
# Arbres, sol, rues
# ---------------------------------------------------------------------------
def add_tree(x, y, r, mat, collection):
    r = r * 0.6
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.07, depth=TREE_TRUNK_H + r,
                                        location=(x, y, (TREE_TRUNK_H + r) / 2))
    trunk = bpy.context.active_object
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, TREE_TRUNK_H + r * 0.9))
    crown = bpy.context.active_object
    for ob in (trunk, crown):
        ob.data.materials.append(mat)
        for c in ob.users_collection:
            c.objects.unlink(ob)
        collection.objects.link(ob)
    crown.name, trunk.name = "Arbre", "Tronc"


def add_waves(bm, rings, z):
    """Vaguelettes : petits traits horizontaux en quinconce dans chaque case d'eau (l'eau est blanche sinon)."""
    ext = rings[0]
    xs, ys = [p[0] for p in ext], [p[1] for p in ext]
    x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(round(max(xs))), int(round(max(ys)))
    for cy in range(y0, y1):
        for cx in range(x0, x1):
            u = cx + 0.5 + (0.25 if cy % 2 else -0.25)
            v = cy + 0.5
            # trait : arête relevée d'une bande très fine (Freestyle la dessine comme un contour)
            a = bm.verts.new(Vector((u - WAVE_L / 2, v, z)))
            b = bm.verts.new(Vector((u + WAVE_L / 2, v, z)))
            c = bm.verts.new(Vector((u + WAVE_L / 2, v, z + WAVE_H)))
            d = bm.verts.new(Vector((u - WAVE_L / 2, v, z + WAVE_H)))
            try:
                bm.faces.new([a, b, c, d])
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Caméra + rendu
# ---------------------------------------------------------------------------
def setup_camera(scene, bounds, width_px, turn=ISO_TURN, tilt=ISO_TILT, paper=None):
    x0, y0, x1, y1 = bounds
    center = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    cam_data = bpy.data.cameras.new("CamIso")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("CamIso", cam_data)
    scene.collection.objects.link(cam)
    cam.rotation_euler = (math.radians(tilt), 0.0, math.radians(turn))
    direction = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    dist = 3.0 * max(x1 - x0, y1 - y0)
    cam.location = center - direction * dist
    cam_data.clip_end = dist * 4
    scene.camera = cam
    bpy.context.view_layer.update()

    # étendue projetée du périmètre (boîte au sol + MAX_Z de hauteur)
    inv = cam.matrix_world.inverted()
    xs, ys = [], []
    for x in (x0, x1):
        for y in (y0, y1):
            for z in (0.0, MAX_Z):
                p = inv @ Vector((x, y, z))
                xs.append(p.x)
                ys.append(p.y)
    w, h = (max(xs) - min(xs)) * 1.04, (max(ys) - min(ys)) * 1.04
    # recentrer la caméra sur le centre projeté
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    cam.location += cam.matrix_world.to_3x3() @ Vector((cx, cy, 0))

    if paper:
        # cadre imposé (la feuille) : la ville est posée dedans, le reste est blanc
        fw, fh = w, h
        if fw / fh > paper:
            fh = fw / paper
        else:
            fw = fh * paper
        res_x, res_y = int(width_px), int(round(width_px / paper))
        cam_data.ortho_scale = fh if res_y >= res_x else fw
        fill = (w * h) / (fw * fh)
    else:
        res_x, res_y = int(width_px), int(round(width_px * h / w))
        cam_data.ortho_scale = max(w, h)
        fill = 1.0

    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    print("cadrage : ville %.3f:1, image %d × %d, remplissage %.1f %%"
          % (w / h, res_x, res_y, 100 * fill))


def setup_render(scene, out_dir, name="castres"):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.cycles.device = "CPU"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("Monde")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 1.0

    # Freestyle : silhouettes, arêtes, bords — lignes cachées supprimées
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = "ABSOLUTE"
    scene.render.line_thickness = LINE_THICKNESS
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(134.0)
    fs.use_culling = True
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    ls = fs.linesets.new("LigneClaire")
    ls.select_silhouette = True
    ls.select_crease = True
    ls.select_border = True
    ls.select_contour = False
    ls.select_external_contour = False
    ls.select_material_boundary = False
    ls.select_edge_mark = False
    ls.select_by_visibility = True
    ls.visibility = "VISIBLE"
    st = ls.linestyle
    st.color = (0, 0, 0)
    st.thickness = LINE_THICKNESS
    st.caps = "ROUND"

    # export SVG (add-on livré avec Blender)
    try:
        bpy.ops.preferences.addon_enable(module="render_freestyle_svg")
        scene.svg_export.use_svg_export = True
        scene.svg_export.mode = "FRAME"
        scene.svg_export.split_at_invisible = True
    except Exception as e:  # noqa
        print("SVG export indisponible :", e)

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = os.path.join(out_dir, name + ".png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        argv = sys.argv[1:]
    if len(argv) < 2:
        print("Usage : python3 02_build_blender.py blocks.json out/ [largeur_px] [orientation]")
        sys.exit(1)
    geojson_path, out_dir = argv[0], argv[1]
    width_px = int(argv[2]) if len(argv) > 2 else 4000
    turn = float(argv[3]) if len(argv) > 3 else ISO_TURN
    tilt = float(argv[4]) if len(argv) > 4 else ISO_TILT
    paper = None
    if len(argv) > 5 and argv[5] not in ("libre", "-", ""):
        paper = float(argv[5])   # largeur / hauteur de la feuille, ex. 75/110 = 0.682
    os.makedirs(out_dir, exist_ok=True)

    with open(geojson_path) as f:
        data = json.load(f)

    clear_scene()
    scene = bpy.context.scene
    mat = white_material()
    col = bpy.data.collections.new("Ville")
    scene.collection.children.link(col)

    bm_vol, bm_win, bm_lm, bm_par = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    bm_ground = {k: bmesh.new() for k in GROUND_Z}
    bm_waves = bmesh.new()
    counts = {}

    for ft in data["features"]:
        props, geom = ft["properties"], ft["geometry"]
        kind = props["kind"]
        counts[kind] = counts.get(kind, 0) + 1
        if geom["type"] == "Point":
            if kind == "tree":
                x, y = geom["coordinates"]
                add_tree(x, y, props.get("radius", 0.8), mat, col)
            continue
        if geom["type"] != "Polygon":
            continue
        rings = rings_of(geom)
        if not rings:
            continue
        if kind in ("volume", "landmark"):
            bm = bm_lm if kind == "landmark" else bm_vol
            h = float(props.get("height", props.get("levels", 2))) * LEVEL_H
            roof = props.get("roof", "plat")
            walls = build_volume(bm, rings, h, "pignon" if roof == "pignon" else "plat")
            if roof == "terrasse":
                add_parapet(bm_par, rings, h)
            add_windows(bm_win, walls, props.get("levels", 2), props.get("motif", "carre"))
        elif kind in GROUND_Z:
            add_flat_polygon(bm_ground[kind], rings, GROUND_Z[kind])
            if kind == "water":
                add_waves(bm_waves, rings, GROUND_Z[kind])

    new_object("Volumes", bm_vol, mat, col)
    new_object("Fenetres", bm_win, mat, col)
    new_object("Monuments", bm_lm, mat, col)
    new_object("GardeCorps", bm_par, mat, col)
    new_object("Vagues", bm_waves, mat, col)
    for k, bm in bm_ground.items():
        new_object("Sol_" + k, bm, mat, col)

    # sol blanc, bien plus grand que le cadre
    x0, y0, x1, y1 = data["bounds"]
    bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, 0))
    ground = bpy.context.active_object
    ground.scale = ((x1 - x0) * 6, (y1 - y0) * 6, 1)
    ground.name = "Sol"
    ground.data.materials.append(mat)

    setup_camera(scene, data["bounds"], width_px, turn, tilt, paper)
    name = os.environ.get("CASTRES_NAME") or ("castres" if (turn, tilt) == (ISO_TURN, ISO_TILT) else "castres_%03d_%02d" % (int(turn), int(tilt)))
    setup_render(scene, out_dir, name)
    print("Scène :", counts, "| image", scene.render.resolution_x, "×", scene.render.resolution_y, "| orientation", turn, "| inclinaison", tilt)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, name + ".blend"))
    bpy.ops.render.render(write_still=True)
    print("Rendu écrit dans", scene.render.filepath)


if __name__ == "__main__":
    main()
