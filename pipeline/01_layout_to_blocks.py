#!/usr/bin/env python3
"""
01_layout_to_blocks.py — Fiche 004 : du plan de jeu (data/layout.json) aux
volumes (data/blocks.json), sans IA, déterministe, graine fixe.

Règles (Louis, 18/09) :
- îlot ordinaire (composante de cases I) : 1 à 2 boîtes (plus grand rectangle
  inscrit, puis le reste), 2 ou 3 niveaux, 3 niveaux max partout ;
- maison unique (m) : 1 boîte à 2 niveaux, toit à 2 pans ;
- toute boîte bordant une venelle de 1 case : 2 niveaux max, pour qu'on voie
  la venelle en isométrie ;
- toit plat par défaut, 30 % des toits plats avec terrasse jouable
  (garde-corps) ;
- rez-de-chaussée en vitrine sur les quatre rues nommées et sur tout le tour
  de la place ; motifs carré / haute / arcade ailleurs, aléatoire à graine
  fixe ;
- monuments : boîte à leur emprise, 3 niveaux, clocher de 6 niveaux sur la
  cathédrale, fronton sur le théâtre ; le jardin = parc avec allées et arbres
  en grille ; la place = dallage avec deux rangées de platanes ;
- 1 case = 1 unité Blender ; un niveau = 1 case de haut (DECISIONS.md).

Sorties :
  data/blocks.json      — GeoJSON (features + bounds) lu par 02_build_blender.py
  out/blocks_preview.png — vue du dessus, hauteur écrite sur chaque boîte

Usage :
  python3 pipeline/01_layout_to_blocks.py [data/layout.json] [data/blocks.json] [out/blocks_preview.png]

Dépendances : pillow (aperçu). Entrée facultative : data/streets_index.json
(cases par voie, écrit par 00_osm_to_layout.py) pour repérer les rues nommées.
"""

import json
import os
import random
import sys
from collections import Counter, deque

SEED = 42
LEVEL_CHOICES = [2, 3, 3]          # tirage pondéré : deux tiers de 3 niveaux
MAX_LEVELS = 3
TERRACE_SHARE = 0.30
ANNEX_MIN = 6  # 3e boîte d'un îlot seulement si le reste offre un rectangle d'au moins 6 cases
MOTIFS = ["carre", "haute", "arcade"]
MOTIF_WEIGHTS = [0.5, 0.35, 0.15]
NAMED_KIND_PREFIX = "rue nommée"    # les quatre rues nommées de DECISIONS (largeur 4)
INSET_BIG, INSET_SMALL = 0.35, 0.15 # trottoir : recul des boîtes par rapport à la case
CLOCHER_LEVELS = 6
TREE_R = 0.9                        # rayon de la boule (diamètre 1,5–2 cases)
STREET_TREE_R = 0.75


# ---------------------------------------------------------------------------
# outils de grille
# ---------------------------------------------------------------------------
def components(cells):
    """Composantes 4-connexes d'un ensemble de cases."""
    cells = set(cells)
    out = []
    while cells:
        start = next(iter(cells))
        q = deque([start]); cells.discard(start); comp = [start]
        while q:
            x, y = q.popleft()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in cells:
                    cells.discard(n); q.append(n); comp.append(n)
        out.append(comp)
    return out


def largest_rect(cells):
    """Plus grand rectangle (en surface) inscrit dans un ensemble de cases.
    Renvoie (x, y, w, h) ou None."""
    cells = set(cells)
    if not cells:
        return None
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W = x1 - x0 + 1
    heights = [0] * W
    best, best_area = None, 0
    for y in range(y0, y1 + 1):
        for i in range(W):
            heights[i] = heights[i] + 1 if (x0 + i, y) in cells else 0
        # plus grand rectangle dans l'histogramme
        stack = []
        for i in range(W + 1):
            h = heights[i] if i < W else 0
            start = i
            while stack and stack[-1][1] >= h:
                idx, hh = stack.pop()
                area = hh * (i - idx)
                if area > best_area:
                    best_area, best = area, (x0 + idx, y - hh + 1, i - idx, hh)
                start = idx
            stack.append((start, h))
    return best


def rect_cells(r):
    x, y, w, h = r
    return {(x + i, y + j) for i in range(w) for j in range(h)}


def rects_from_mask(cells):
    """Découpe un ensemble de cases en rectangles (séries horizontales fusionnées
    verticalement quand elles sont identiques)."""
    cells = set(cells)
    rows = {}
    for x, y in cells:
        rows.setdefault(y, []).append(x)
    runs = {}
    for y, xs in rows.items():
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is None or x != prev + 1:
                runs.setdefault((start, prev), []).append(y)
                if x is not None:
                    start = x
            if x is not None:
                prev = x
    out = []
    for (xa, xb), ys in runs.items():
        ys.sort()
        y_start = y_prev = ys[0]
        for y in ys[1:] + [None]:
            if y is None or y != y_prev + 1:
                out.append((xa, y_start, xb - xa + 1, y_prev - y_start + 1))
                if y is not None:
                    y_start = y
            if y is not None:
                y_prev = y
    return out


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------
def build(layout, streets_index):
    rng = random.Random(SEED)
    cols, rows = layout["cols"], layout["rows"]
    grid = layout["cells"].split("\n")
    cell = lambda x, y: grid[y][x] if 0 <= x < cols and 0 <= y < rows else None
    monuments = {m["id"]: m for m in layout["monuments"]}
    log = []

    def say(*a):
        log.append(" ".join(str(x) for x in a)); print(log[-1])

    # --- masques utiles
    street = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] in "rb"}
    narrow = set()                      # venelles de 1 case : voie sans voie de part et d'autre
    for (x, y) in street:
        horiz_free = (x - 1, y) not in street and (x + 1, y) not in street
        vert_free = (x, y - 1) not in street and (x, y + 1) not in street
        if horiz_free or vert_free:
            narrow.add((x, y))
    named = set()
    for st in streets_index or []:
        if st.get("decisions") and st.get("kind", "").startswith(NAMED_KIND_PREFIX):
            named |= {tuple(c) for c in st["cells"]}
    place = None
    for m in layout.get("labels", []):
        pass
    # la place : le rectangle de cases 'p'
    pcells = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == "p"}
    place = largest_rect(pcells) if pcells else None
    place_ring = set()
    if place:
        px, py, pw, ph = place
        place_ring = {(x, y) for x in range(px - 1, px + pw + 1) for y in range(py - 1, py + ph + 1)} - rect_cells(place)

    # --- cases de monuments (dans leurs rectangles), pour les exclure des îlots ordinaires
    landmark_cells = {}
    for mid, m in monuments.items():
        if mid.startswith("pont-"):
            continue
        ch = "P" if mid == "jardin-eveche" else "I"
        cs = {(x, y) for (x, y) in rect_cells((m["x"], m["y"], m["w"], m["h"])) if cell(x, y) == ch}
        landmark_cells[mid] = cs
    all_landmark = set().union(*landmark_cells.values()) if landmark_cells else set()

    boxes = []
    dropped_cells = 0

    def neighbours(cells_):
        out = set()
        for (x, y) in cells_:
            out |= {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)}
        return out - set(cells_)

    def make_box(r, kind, levels, roof, motif, mid=None):
        x, y, w, h = r
        inset = INSET_BIG if min(w, h) >= 2 else INSET_SMALL
        boxes.append(dict(x=x, y=y, w=w, h=h, inset=inset, levels=levels, roof=roof, motif=motif, kind=kind, id=mid))
        return boxes[-1]

    def levels_for(r, base):
        # règle venelle : une boîte qui borde une venelle de 1 case → 2 niveaux max
        if neighbours(rect_cells(r)) & narrow:
            return min(base, 2)
        return min(base, MAX_LEVELS)

    def motif_for(r):
        nb = neighbours(rect_cells(r))
        if nb & named or nb & place_ring or nb & rect_cells(place) if place else nb & named:
            return "vitrine"
        return rng.choices(MOTIFS, MOTIF_WEIGHTS)[0]

    def roof_for(kind):
        if kind == "house":
            return "pignon"
        return "terrasse" if rng.random() < TERRACE_SHARE else "plat"

    # --- îlots ordinaires : 1 à 2 boîtes
    ordinary = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == "I"} - all_landmark
    n_blocks = n_two = n_three = 0
    leftover = set()
    for comp in components(ordinary):
        remaining = set(comp)
        n_blocks += 1
        for k in range(3):
            r = largest_rect(remaining)
            # 2e boîte seulement si ≥ 4 cases ; 3e boîte (annexe) seulement si ≥ ANNEX_MIN cases
            if r is None or (k == 1 and r[2] * r[3] < 4) or (k == 2 and r[2] * r[3] < ANNEX_MIN):
                break
            kind = "building"
            base = rng.choice(LEVEL_CHOICES)
            make_box(r, kind, levels_for(r, base), roof_for(kind), motif_for(r))
            remaining -= rect_cells(r)
            if k == 1:
                n_two += 1
            if k == 2:
                n_three += 1
        dropped_cells += len(remaining)
        leftover |= remaining
    say(f"îlots ordinaires : {n_blocks}, dont {n_two} à deux boîtes et {n_three} à trois ; {dropped_cells} cases restantes → trottoir")

    # --- maisons uniques : 1 boîte, 2 niveaux, 2 pans
    houses = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == "m"}
    n_houses = 0
    for comp in components(houses):
        r = largest_rect(comp)
        if r:
            make_box(r, "house", 2, "pignon", motif_for(r)); n_houses += 1
    say(f"maisons uniques : {n_houses}")

    # --- monuments
    for mid, cs in landmark_cells.items():
        m = monuments[mid]
        if mid == "jardin-eveche" or not cs:
            continue
        for r in rects_from_mask(cs):
            b = make_box(r, "landmark", MAX_LEVELS, "plat", "haute", mid)
        say(f"monument {mid} : {len(rects_from_mask(cs))} boîte(s), {MAX_LEVELS} niveaux")
    extras = []
    if "saint-benoit" in monuments:
        m = monuments["saint-benoit"]
        # clocher : 2 × 2 cases à l'angle nord-ouest de la boîte, 6 niveaux
        extras.append(dict(kind="landmark", x=m["x"], y=m["y"], w=2, h=2, inset=0.1, levels=CLOCHER_LEVELS, roof="plat", motif="none", id="saint-benoit-clocher"))
        say("clocher : 2 × 2 cases, 6 niveaux, angle nord-ouest de la cathédrale")
    if "theatre" in monuments:
        m = monuments["theatre"]
        # fronton : mur mince à 2 pans sur la façade nord, sur toute la largeur
        extras.append(dict(kind="fronton", x=m["x"], y=m["y"], w=m["w"], h=1, inset=0.1, levels=MAX_LEVELS, roof="pignon", motif="none", id="theatre-fronton"))
        say("fronton : façade nord du théâtre")

    # --- sol : voies, quais, eau, parcs, place
    ground = []
    trees = []
    for ch, kind in (("r", "road"), ("b", "road"), ("q", "sidewalk"), ("w", "water")):
        cs = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == ch}
        for r in rects_from_mask(cs):
            ground.append(dict(kind=kind, rect=r, sub=ch))
    # restes d'îlots non bâtis → trottoir (parvis)
    for r in rects_from_mask(leftover):
        ground.append(dict(kind="sidewalk", rect=r, sub="parvis"))
    # boulevards plantés : un arbre tous les 3 cases le long de chaque bord bâti, à 1/2 case du bord
    bcells = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == "b"}
    n_btrees = 0
    for (x, y) in sorted(bcells):
        if (x + y) % 3:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            out = cell(x + dx, y + dy)
            if out in ("I", "m", "q", "P", "p") and (x - dx, y - dy) in bcells:
                trees.append(dict(x=x + .5 + dx * 0.15, y=y + .5 + dy * 0.15, r=STREET_TREE_R))
                n_btrees += 1
                break
    say(f"boulevards : {n_btrees} arbres d'alignement")
    # parcs (dont le jardin) : arbres en grille tous les 3, hors bord ; allées en croix dans le jardin
    parks = {(x, y) for y in range(rows) for x in range(cols) if grid[y][x] == "P"}
    for r in rects_from_mask(parks):
        ground.append(dict(kind="park", rect=r))
    for (x, y) in sorted(parks):
        if x % 3 == 1 and y % 3 == 1 and all(n in parks for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
            trees.append(dict(x=x + .5, y=y + .5, r=TREE_R))
    if "jardin-eveche" in monuments:
        j = monuments["jardin-eveche"]
        jc = landmark_cells.get("jardin-eveche", set())
        cx, cy = j["x"] + j["w"] // 2, j["y"] + j["h"] // 2
        allee_v = {(cx, y) for y in range(j["y"], j["y"] + j["h"]) if (cx, y) in jc}
        allee_h = {(x, cy) for x in range(j["x"], j["x"] + j["w"]) if (x, cy) in jc}
        for r in rects_from_mask(allee_v | allee_h):
            ground.append(dict(kind="sidewalk", rect=r, sub="allee"))
        trees = [t for t in trees if not ((int(t["x"]), int(t["y"])) in (allee_v | allee_h))]
        say(f"jardin : {len(jc)} cases, allées en croix, arbres en grille")
    if place:
        px, py, pw, ph = place
        ground.append(dict(kind="place", rect=place))
        long_h = pw >= ph
        if long_h:
            for i in range(1, pw - 1, 2):
                trees += [dict(x=px + i + .5, y=py + 1.2, r=TREE_R), dict(x=px + i + .5, y=py + ph - 1.2, r=TREE_R)]
        else:
            for j in range(1, ph - 1, 2):
                trees += [dict(x=px + 1.2, y=py + j + .5, r=TREE_R), dict(x=px + pw - 1.2, y=py + j + .5, r=TREE_R)]
        say(f"place : dallage {pw} × {ph}, deux rangées de platanes")

    stats = Counter()
    for b in boxes:
        stats[f"{b['kind']} {b['levels']} niv. {b['roof']}"] += 1
    say("boîtes : " + ", ".join(f"{k} × {n}" for k, n in sorted(stats.items())))
    say(f"vitrines : {sum(1 for b in boxes if b['motif'] == 'vitrine')} boîtes ; arbres : {len(trees)}")
    return boxes, extras, ground, trees, log


# ---------------------------------------------------------------------------
# sorties
# ---------------------------------------------------------------------------
def to_geojson(layout, boxes, extras, ground, trees):
    rows = layout["rows"]
    fy = lambda y: rows - y                       # y de la grille vers le bas → Blender y vers le haut

    def rect_poly(x, y, w, h, inset=0.0):
        x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
        return [[[x0, fy(y1)], [x1, fy(y1)], [x1, fy(y0)], [x0, fy(y0)], [x0, fy(y1)]]]

    feats = []
    for b in boxes + extras:
        kind = "volume" if b["kind"] in ("building", "house", "fronton") else "landmark"
        props = dict(kind=kind, levels=b["levels"], height=float(b["levels"]), roof=b["roof"], motif=b["motif"],
                     sub=b["kind"], id=b.get("id"))
        if b["kind"] == "fronton":
            props.update(height=float(b["levels"]), motif="none")
        feats.append(dict(type="Feature", properties=props,
                          geometry=dict(type="Polygon", coordinates=rect_poly(b["x"], b["y"], b["w"], b["h"], b["inset"]))))
    for g in ground:
        x, y, w, h = g["rect"]
        feats.append(dict(type="Feature", properties=dict(kind=g["kind"], sub=g.get("sub", "")),
                          geometry=dict(type="Polygon", coordinates=rect_poly(x, y, w, h))))
    for t in trees:
        feats.append(dict(type="Feature", properties=dict(kind="tree", radius=t["r"]),
                          geometry=dict(type="Point", coordinates=[t["x"], fy(t["y"])])))
    return dict(type="FeatureCollection", bounds=[0, 0, layout["cols"], layout["rows"]],
                cell_unit=1.0, level_height=1.0, features=feats)


def preview(layout, boxes, extras, trees, path, cell=20, margin=40):
    from PIL import Image, ImageDraw
    import importlib.util
    spec = importlib.util.spec_from_file_location("fond", os.path.join(os.path.dirname(os.path.abspath(__file__)), "00b_osm_to_fond.py"))
    fond = importlib.util.module_from_spec(spec); spec.loader.exec_module(fond)
    cols, rows = layout["cols"], layout["rows"]
    COLORS = {"r": (232, 232, 232), "b": (214, 222, 206), "I": (244, 236, 226), "m": (244, 236, 226), "p": (248, 232, 170),
              "P": (200, 228, 196), "w": (160, 200, 232), "q": (226, 216, 196), ".": (255, 255, 255)}
    img = Image.new("RGB", (cols * cell + 2 * margin, rows * cell + 2 * margin + 40), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ox, oy = margin, margin + 40
    for y, row in enumerate(layout["cells"].split("\n")):
        for x, c in enumerate(row):
            d.rectangle([ox + x * cell, oy + y * cell, ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1], fill=COLORS.get(c, (255, 0, 255)))
    fnt = fond.load_font(13); big = fond.load_font(20)
    fills = {"building": (201, 162, 126), "house": (166, 118, 80), "landmark": (150, 110, 150), "fronton": (150, 110, 150)}
    for b in boxes + extras:
        x0, y0 = ox + (b["x"] + b["inset"]) * cell, oy + (b["y"] + b["inset"]) * cell
        x1, y1 = ox + (b["x"] + b["w"] - b["inset"]) * cell, oy + (b["y"] + b["h"] - b["inset"]) * cell
        d.rectangle([x0, y0, x1, y1], fill=fills[b["kind"]], outline=(0, 0, 0), width=2 if b["kind"] in ("landmark", "fronton") else 1)
        tag = str(b["levels"]) + {"terrasse": "T", "pignon": "^", "plat": ""}[b["roof"]] + ("v" if b["motif"] == "vitrine" else "")
        tw = d.textlength(tag, font=fnt)
        d.text(((x0 + x1) / 2 - tw / 2, (y0 + y1) / 2 - 7), tag, fill=(0, 0, 0), font=fnt)
    for t in trees:
        cx, cy, r = ox + t["x"] * cell, oy + t["y"] * cell, t["r"] * cell
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 110, 40), width=2)
    d.text((margin, 10), "Fiche 004 — volumes : chiffre = niveaux, T = terrasse, ^ = 2 pans, v = vitrine au rez-de-chaussée, cercle = arbre ; monuments en violet", fill=(0, 0, 0), font=big)
    img.save(path)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data/layout.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/blocks.json"
    png = sys.argv[3] if len(sys.argv) > 3 else "out/blocks_preview.png"
    with open(src, encoding="utf-8") as f:
        layout = json.load(f)
    idx_path = os.path.join(os.path.dirname(src) or ".", "streets_index.json")
    streets_index = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else None
    if streets_index is None:
        print("ATTENTION : pas de streets_index.json, les vitrines ne seront posées qu'autour de la place")
    boxes, extras, ground, trees, log = build(layout, streets_index)
    gj = to_geojson(layout, boxes, extras, ground, trees)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    print(f"écrit {out} ({len(gj['features'])} features)")
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    preview(layout, boxes, extras, trees, png)
    print(f"écrit {png}")


if __name__ == "__main__":
    main()
