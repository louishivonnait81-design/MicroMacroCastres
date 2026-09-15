#!/usr/bin/env python3
"""
00_osm_to_layout.py — Fiche 002, partie A : brouillon automatique du plan de
jeu à partir de data/castres.osm.

Ce que fait le script, dans l'ordre (voir tasks/002_layout_editor.md) :
  1. projette le périmètre de DECISIONS.md sur la grille 106 × 71 avec le
     facteur de compression fixé (0,097 case/m ; marge de 16 cases à l'est)
  2. garde les boulevards, les rues principales (primary / secondary /
     tertiary OSM), les cinq rues nommées et les ponts ; redresse chaque
     rue sur les axes 0° / 90° ; largeur 4 cases, 6 pour les boulevards
  3. pose l'eau (Agout élargi à ≥ 8 cases), les quais (2 cases), la place
     Jean-Jaurès (≥ 18 cases), le jardin de l'Évêché, les autres parcs
  4. réserve les rectangles des monuments de DECISIONS.md (position OSM)
  5. tout le reste devient îlot ; les îlots de plus de MAX_BLOCK cases de
     côté sont coupés par une rue intérieure de 3 cases, et on répète en
     abaissant MAX_BLOCK jusqu'à ce que rues + places + parcs ≥ 33 %
  6. écrit data/layout.json, data/fond_castres_grille.png (fond recadré sur
     la grille pour l'éditeur) et out/layout_preview.png (PNG de contrôle)

Usage :
  python3 pipeline/00_osm_to_layout.py
  python3 pipeline/00_osm_to_layout.py --osm data/castres.osm --out data/layout.json \
      --preview out/layout_preview.png --max-block 12

Dépendances : pillow ; réutilise pipeline/00b_osm_to_fond.py pour lire l'OSM.
"""

import argparse
import importlib.util
import json
import math
import os
import re
from collections import deque

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fond", os.path.join(HERE, "00b_osm_to_fond.py"))
fond = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fond)

# ---------------------------------------------------------------------------
# Paramètres — tout ce qui vient de DECISIONS.md
# ---------------------------------------------------------------------------
COLS, ROWS = 106, 71
# Périmètre : bd Léon Bourgeois → Agout / Villegoudou, bd Miredames → bd Henri
# Sizaire. Le facteur est calé sur la hauteur ; la largeur qui reste va à l'est.
PERIM = dict(south=43.6010, west=2.2335, north=43.6076, east=2.2450)

STREET_W, BOULEVARD_W, INNER_W = 4, 6, 3
MAIN_CLASSES = {"primary", "secondary", "tertiary", "primary_link", "secondary_link", "tertiary_link"}
NAMED_STREETS = [r"Rue Sabatier$", r"Rue Frédéric Thomas", r"Rue Victor Hugo", r"Rue de l'Hôtel de Ville",
                 r"Rue Villegoudou", r"Quai des Jacobins", r"^Pont Vieux", r"^Pont Neuf"]
SKIP_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "footway", "path", "steps",
                "cycleway", "service", "track", "bus_stop", "platform", "proposed", "construction"}

WATER_MIN_W = 8          # cases : l'Agout fait 8–12 cases
QUAI_W = 2
PLACE_MIN, PLACE_MAX = 18, 24
JARDIN_W, JARDIN_H = 14, 10

MONUMENTS = [            # id, regex sur le nom OSM, (w, h) cases, niveaux
    ("saint-benoit", r"Cathédrale Saint-Beno[iî]t", (10, 14), 3),
    ("eveche", r"Musée Goya|Palais épiscopal|Hôtel de [Vv]ille", (12, 7), 3),
    ("theatre", r"Théâtre [Mm]unicipal", (7, 6), 3),
]
OPEN = "rpP"
TARGET_SHARE = 33.0

COLORS = {"r": (227, 227, 227), "I": (201, 162, 126), "p": (243, 214, 107), "P": (159, 211, 155),
          "w": (142, 193, 230), "q": (220, 205, 176), ".": (255, 255, 255)}
LEGEND = {"r": "rue", "I": "ilot", "p": "place", "P": "parc", "w": "eau", "q": "quai", ".": "vide"}


# ---------------------------------------------------------------------------
# Projection périmètre → grille
# ---------------------------------------------------------------------------
class Grid:
    def __init__(self, perim):
        self.s, self.w, self.n = perim["south"], perim["west"], perim["north"]
        lat0 = (self.s + self.n) / 2
        self.kx = 111320 * math.cos(math.radians(lat0))
        self.ky = 111320
        h_m = (self.n - self.s) * self.ky
        self.f = ROWS / h_m                       # cases par mètre
        self.e = self.w + COLS / self.f / self.kx  # est réel de la grille (marge incluse)
        self.perim_w_m = (perim["east"] - self.w) * self.kx
        self.h_m = h_m

    def cell(self, latlon):
        """Coordonnées continues en cases (x vers l'est, y vers le sud)."""
        lat, lon = latlon
        return ((lon - self.w) * self.kx * self.f, (self.n - lat) * self.ky * self.f)

    def bbox(self):
        return (self.s, self.w, self.n, self.e)


def inside(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


# ---------------------------------------------------------------------------
# Géométrie : simplification et redressement
# ---------------------------------------------------------------------------
def douglas_peucker(pts, tol):
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * px - dx * py + x1 * y0 - y1 * x0) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return douglas_peucker(pts[:idx + 1], tol)[:-1] + douglas_peucker(pts[idx:], tol)
    return [pts[0], pts[-1]]


def rectify(p, q, jog=2, step=6):
    """Découpe le segment p→q en morceaux horizontaux / verticaux (cases entières).
    - écart sur l'axe mineur ≤ jog : segment droit sur l'axe majeur (les
      épaisseurs de 4 cases se recouvrent, pas de trou visible)
    - sinon : escalier dont chaque marche vaut ≈ step cases sur l'axe mineur,
      donc au moins la largeur d'une rue : chaque marche se lit comme un coin"""
    (x0, y0), (x1, y1) = p, q
    dx, dy = x1 - x0, y1 - y0
    horiz = abs(dx) >= abs(dy)
    major, minor = (abs(dx), abs(dy)) if horiz else (abs(dy), abs(dx))
    pieces = []
    if minor <= jog:
        pieces.append(((x0, y0), (x1, y0)) if horiz else ((x0, y0), (x0, y1)))
    else:
        n = max(1, round(minor / step))
        x, y = x0, y0
        for i in range(1, n + 1):
            tx = x0 + round(dx * i / n)
            ty = y0 + round(dy * i / n)
            if horiz:
                pieces += [((x, y), (tx, y)), ((tx, y), (tx, ty))]
            else:
                pieces += [((x, y), (x, ty)), ((x, ty), (tx, ty))]
            x, y = tx, ty
    return pieces


def stamp_line(grid, a, b, w, ch, allow=None):
    """Trace un segment axial d'épaisseur w (cases). allow(x, y) filtre les cases."""
    (x0, y0), (x1, y1) = a, b
    lo = -(w // 2)
    hi = lo + w
    if y0 == y1:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for d in range(lo, hi):
                y = y0 + d
                if inside(x, y) and (allow is None or allow(x, y)):
                    grid[y][x] = ch
    else:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for d in range(lo, hi):
                x = x0 + d
                if inside(x, y) and (allow is None or allow(x, y)):
                    grid[y][x] = ch


def fill_polygon(grid, ring, ch, allow=None):
    """Remplit un polygone (coordonnées cases continues) : test du centre de case."""
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1 = max(0, int(min(xs))), min(COLS - 1, int(max(xs)) + 1)
    y0, y1 = max(0, int(min(ys))), min(ROWS - 1, int(max(ys)) + 1)
    n = len(ring)
    for y in range(y0, y1 + 1):
        cy = y + 0.5
        xings = []
        for i in range(n):
            (ax, ay), (bx, by) = ring[i], ring[(i + 1) % n]
            if (ay <= cy) != (by <= cy):
                xings.append(ax + (cy - ay) * (bx - ax) / (by - ay))
        xings.sort()
        for i in range(0, len(xings) - 1, 2):
            for x in range(max(x0, int(math.ceil(xings[i] - 0.5))), min(x1, int(math.floor(xings[i + 1] - 0.5))) + 1):
                if allow is None or allow(x, y):
                    grid[y][x] = ch


def fill_rect(grid, x, y, w, h, ch, allow=None):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if inside(xx, yy) and (allow is None or allow(xx, yy)):
                grid[yy][xx] = ch


def dilate(grid, src, dst, times):
    for _ in range(times):
        add = []
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] in src:
                    continue
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if inside(nx, ny) and grid[ny][nx] in src:
                        add.append((x, y)); break
        for x, y in add:
            grid[y][x] = dst


def components(grid, ch, protected):
    """Composantes 4-connexes des cases == ch et non protégées."""
    seen = [[False] * COLS for _ in range(ROWS)]
    comps = []
    for y in range(ROWS):
        for x in range(COLS):
            if seen[y][x] or grid[y][x] != ch or protected[y][x]:
                continue
            q = deque([(x, y)]); seen[y][x] = True; cells = []
            while q:
                cx, cy = q.popleft(); cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if inside(nx, ny) and not seen[ny][nx] and grid[ny][nx] == ch and not protected[ny][nx]:
                        seen[ny][nx] = True; q.append((nx, ny))
            comps.append(cells)
    return comps


def bbox_of(cells):
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


# ---------------------------------------------------------------------------
# Lecture OSM → objets en cases
# ---------------------------------------------------------------------------
def collect(osm_path, g):
    nodes, ways, rels = fond.parse_osm(osm_path)
    named_re = [re.compile(p) for p in NAMED_STREETS]

    def coords(way):
        return [g.cell(nodes[n]) for n in way["nodes"] if n in nodes]

    streets, water, parks, place, jardin = [], [], [], [], []
    features = {}          # nom → liste de rings/polylines pour les monuments
    for wid, way in ways.items():
        t = way["tags"]
        name = t.get("name", "")
        hw = t.get("highway")
        pts = coords(way)
        closed = len(way["nodes"]) > 3 and way["nodes"][0] == way["nodes"][-1]
        if hw and hw not in SKIP_CLASSES and t.get("area") != "yes" and len(pts) >= 2:
            keep = hw in MAIN_CLASSES or any(r.search(name) for r in named_re) or name.startswith("Boulevard")
            if keep:
                w = BOULEVARD_W if name.startswith("Boulevard") else STREET_W
                streets.append(dict(name=name, pts=pts, w=w, bridge=t.get("bridge") == "yes" or name.startswith("Pont ")))
        if closed and len(pts) >= 4:
            if t.get("natural") == "water" or t.get("water") in ("river", "canal") or t.get("waterway") == "riverbank":
                water.append(pts)
            elif t.get("leisure") in ("park", "garden"):
                (jardin if re.search(r"Jardin de l'?[ÉE]v[êe]ch[ée]", name) else parks).append(pts)
            elif re.search(r"Place Jean[- ]Jaur[èe]s", name) and (t.get("place") == "square" or t.get("area") == "yes" or hw):
                place.append(pts)
        if name:
            features.setdefault(name, []).append((pts, closed, t))
    for rid, rel in rels.items():
        t = rel["tags"]
        name = t.get("name", "")
        rings = fond.rel_outer_rings(rel, ways, nodes)
        rings = [[g.cell(p) for p in r] for r in rings]
        if t.get("natural") == "water" or t.get("water") in ("river", "canal") or t.get("waterway") == "riverbank":
            water += rings
        elif t.get("leisure") in ("park", "garden"):
            (jardin if re.search(r"Jardin de l'?[ÉE]v[êe]ch[ée]", name) else parks).extend(rings)
        elif re.search(r"Place Jean[- ]Jaur[èe]s", name):
            place += rings
        if name:
            for r in rings:
                features.setdefault(name, []).append((r, True, t))
    # nœuds nommés (un musée peut n'être qu'un point)
    for nid, (lat, lon) in nodes.items():
        pass
    return streets, water, parks, place, jardin, features, nodes


def feature_center(features, pattern):
    rx = re.compile(pattern)
    best = None
    for name, items in features.items():
        if not rx.search(name):
            continue
        for pts, closed, t in items:
            if not pts:
                continue
            if closed and (best is None or len(pts) > len(best[0])):
                best = (pts, name)
            elif best is None:
                best = (pts, name)
    if not best:
        return None, None
    pts, name = best
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), name


def centered_rect(cx, cy, w, h):
    x = int(round(cx - w / 2)); y = int(round(cy - h / 2))
    x = max(0, min(COLS - w, x)); y = max(0, min(ROWS - h, y))
    return x, y, w, h


# ---------------------------------------------------------------------------
# Construction du brouillon
# ---------------------------------------------------------------------------
def build(osm_path, max_block, verbose=True):
    g = Grid(PERIM)
    log = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        log.append(s)
        if verbose:
            print(s)

    say(f"facteur de compression : {g.f:.4f} case/m (1 case = {1 / g.f:.1f} m) ; "
        f"périmètre {g.perim_w_m:.0f} × {g.h_m:.0f} m → {g.perim_w_m * g.f:.0f} × {ROWS} cases, "
        f"marge est {COLS - g.perim_w_m * g.f:.0f} cases")
    streets, water, parks, place, jardin, features, nodes = collect(osm_path, g)
    say(f"OSM : {len(streets)} tronçons de rue conservés, {len(water)} polygones d'eau, "
        f"{len(parks)} parcs, place {len(place)} polygone(s), jardin {len(jardin)} polygone(s)")

    grid = [["."] * COLS for _ in range(ROWS)]
    protected = [[False] * COLS for _ in range(ROWS)]
    monuments, labels = [], []

    # 3a. eau, élargie à WATER_MIN_W, puis quais
    for ring in water:
        fill_polygon(grid, ring, "w")
    widths = [sum(1 for x in range(COLS) if grid[y][x] == "w") for y in range(ROWS)]
    widths = [w for w in widths if w]
    med = sorted(widths)[len(widths) // 2] if widths else 0
    grow = max(0, math.ceil((WATER_MIN_W - med) / 2))
    dilate(grid, "w", "w", grow)
    say(f"Agout : largeur médiane {med} cases → dilatation {grow} → ≥ {med + 2 * grow}")
    dilate(grid, "w", "q", QUAI_W)

    # 3b. parcs, jardin de l'Évêché (rectangle DECISIONS), place Jean-Jaurès (≥ PLACE_MIN)
    for ring in parks:
        fill_polygon(grid, ring, "P", allow=lambda x, y: grid[y][x] == ".")
    jardin_c = None
    if jardin:
        pts = [p for r in jardin for p in r]
        jardin_c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    else:
        say("ATTENTION : jardin de l'Évêché introuvable dans l'OSM")
    place_rect = None
    if place:
        pts = [p for r in place for p in r]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        w0, h0 = max(xs) - min(xs), max(ys) - min(ys)
        scale = max(1.0, PLACE_MIN / max(w0, h0, 1))
        w = int(round(min(PLACE_MAX, max(w0 * scale, PLACE_MIN)))); h = int(round(max(6, min(PLACE_MAX, h0 * scale))))
        x, y, w, h = centered_rect((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, w, h)
        # laisser 4 cases entre la place et la rive pour la rangée de maisons sur l'Agout
        banks = [next((xx for xx in range(COLS) if grid[yy][xx] in "wq"), COLS) for yy in range(y, y + h)]
        x = max(0, min(x, min(banks) - 4 - w))
        place_rect = (x, y, w, h)
        say(f"place Jean-Jaurès : {w0:.0f} × {h0:.0f} cases réelles → {w} × {h}")
    else:
        say("ATTENTION : place Jean-Jaurès introuvable dans l'OSM")

    # 2. rues redressées ; les ponts passent sur l'eau, les autres s'arrêtent à la rive
    named_mid = {}
    for st in streets:
        pts = douglas_peucker(st["pts"], 2.0)
        cells = [(int(round(x)), int(round(y))) for x, y in pts]
        cells = [c for i, c in enumerate(cells) if i == 0 or c != cells[i - 1]]
        allow = None if st["bridge"] else (lambda x, y: grid[y][x] not in "w")
        for a, b in zip(cells, cells[1:]):
            for p, q in rectify(a, b):
                stamp_line(grid, p, q, st["w"], "r", allow)
        if st["name"] and any(re.compile(p).search(st["name"]) for p in NAMED_STREETS[:6]):
            mid = cells[len(cells) // 2]
            named_mid.setdefault(st["name"], []).append(mid)
    for name, mids in named_mid.items():
        mx = sum(m[0] for m in mids) // len(mids); my = sum(m[1] for m in mids) // len(mids)
        labels.append(dict(text=name, x=max(0, min(COLS - 1, mx)), y=max(0, min(ROWS - 1, my))))
    say(f"après les rues : rues + places + parcs = {100 * sum(1 for r in grid for c in r if c in OPEN) / (COLS * ROWS):.1f} %")
    # 3c. la place par-dessus les rues (les rues y débouchent, elles ne la traversent pas)
    if place_rect:
        x, y, w, h = place_rect
        fill_rect(grid, x, y, w, h, "p", allow=lambda x, y: grid[y][x] not in "wq")
        labels.append(dict(text="Place Jean-Jaurès", x=x + w // 2 - 4, y=y + h // 2))

    # 4. monuments : centre OSM, puis décalage jusqu'à ne chevaucher ni l'eau,
    #    ni la place, ni un monument déjà posé (le jardin est posé en premier)
    placed = [dict(x=m["x"], y=m["y"], w=m["w"], h=m["h"]) for m in monuments]
    if place_rect:
        placed.append(dict(zip("xywh", place_rect)))

    def overlaps(a, b):
        return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]

    def on_water(r):
        return any(grid[yy][xx] in "wq" for yy in range(r["y"], r["y"] + r["h"]) for xx in range(r["x"], r["x"] + r["w"]) if inside(xx, yy))

    def settle(r):
        """Première position libre en spirale autour de la position réelle."""
        x0, y0 = r["x"], r["y"]
        best = None
        for radius in range(0, 40):
            cands = [(x0 + dx, y0 + dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)
                     if max(abs(dx), abs(dy)) == radius]
            cands.sort(key=lambda c: (c[0] - x0) ** 2 + (c[1] - y0) ** 2)
            for x, y in cands:
                if x < 0 or y < 0 or x + r["w"] > COLS or y + r["h"] > ROWS:
                    continue
                t = dict(x=x, y=y, w=r["w"], h=r["h"])
                if not any(overlaps(t, b) for b in placed) and not on_water(t):
                    return t
        return r

    def put(mid_, cx, cy, w, h, ch, levels, name):
        x, y, w, h = centered_rect(cx, cy, w, h)
        r = settle(dict(x=x, y=y, w=w, h=h))
        fill_rect(grid, r["x"], r["y"], w, h, ch)
        placed.append(r)
        monuments.append(dict(id=mid_, x=r["x"], y=r["y"], w=w, h=h, levels=levels))
        moved = "" if (r["x"], r["y"]) == (x, y) else f", décalé de ({r['x'] - x:+d}, {r['y'] - y:+d})"
        say(f"monument {mid_} ← « {name} » en {r['x']},{r['y']} ({w} × {h}){moved}")


    for mid_, pattern, (w, h), levels in MONUMENTS:
        c, name = feature_center(features, pattern)
        if not c:
            say(f"ATTENTION : monument {mid_} ({pattern}) introuvable")
            continue
        put(mid_, c[0], c[1], w, h, "I", levels, name)
    if jardin_c:   # posé après l'Évêché, comme sur le terrain : cathédrale, Évêché, jardin du nord au sud
        put("jardin-eveche", jardin_c[0], jardin_c[1], JARDIN_W, JARDIN_H, "P", 0, "Jardin de l'Évêché")
    # ponts : emprise = la rue sur l'eau, d'une rive à l'autre
    for pid, pattern in (("pont-vieux", r"^Pont Vieux"), ("pont-neuf", r"^Pont Neuf")):
        c, name = feature_center(features, pattern)
        if not c:
            say(f"ATTENTION : {pid} introuvable")
            continue
        y = int(round(c[1])); xc = int(round(c[0]))
        # bande de STREET_W lignes centrée sur le pont, d'une rive à l'autre (quais compris)
        y0 = max(0, min(ROWS - STREET_W, y - STREET_W // 2))
        wet = [x for x in range(COLS) if grid[y][x] in "wq"]
        if wet:
            left = max([x for x in wet if x <= xc] or [min(wet)]); right = min([x for x in wet if x >= xc] or [max(wet)])
            while left - 1 >= 0 and grid[y][left - 1] in "wq":
                left -= 1
            while right + 1 < COLS and grid[y][right + 1] in "wq":
                right += 1
            fill_rect(grid, left, y0, right - left + 1, STREET_W, "r")
            monuments.append(dict(id=pid, x=left, y=y0, w=right - left + 1, h=STREET_W, levels=0))
            say(f"monument {pid} ← « {name} » en {left},{y0} ({right - left + 1} × {STREET_W})")
        else:
            say(f"ATTENTION : {pid} trouvé mais pas d'eau à la ligne {y}")
    # maisons sur l'Agout : rive gauche, entre les deux ponts, 4 de large × ≤ 20 de haut
    ponts = sorted([m for m in monuments if m["id"].startswith("pont-")], key=lambda m: m["y"])
    if len(ponts) == 2:
        y0 = ponts[0]["y"] + ponts[0]["h"]; y1 = ponts[1]["y"]
        banks = {}
        for yy in range(y0, y1):
            b = next((x for x in range(COLS) if grid[yy][x] in "wq"), None)
            if b is not None and b >= 4:
                banks[yy] = b
        # rangée alignée : x = rive minimale - 4 ; ligne valide si ses 4 cases sont libres
        x = min(banks.values()) - 4 if banks else None
        ok = lambda yy: yy in banks and all(grid[yy][xx] not in "pwq" for xx in range(x, x + 4)) \
            and not any(overlaps(dict(x=x, y=yy, w=4, h=1), b) for b in placed)
        best, run = None, []
        for yy in range(y0, y1 + 1):
            if yy < y1 and ok(yy):
                run.append(yy)
            else:
                if best is None or len(run) > len(best):
                    best = run
                run = []
        if best and len(best) >= 4:
            h = min(20, len(best)); y = best[0] + (len(best) - h) // 2
            fill_rect(grid, x, y, 4, h, "I")
            placed.append(dict(x=x, y=y, w=4, h=h))
            monuments.append(dict(id="maisons-agout", x=x, y=y, w=4, h=h, levels=3))
            say(f"monument maisons-agout en {x},{y} (4 × {h}), rive gauche entre les ponts")
        else:
            say("ATTENTION : pas de place pour les maisons sur l'Agout entre les ponts")
    for m in monuments:
        for yy in range(m["y"], m["y"] + m["h"]):
            for xx in range(m["x"], m["x"] + m["w"]):
                if inside(xx, yy):
                    protected[yy][xx] = True

    # 5. îlots, découpe, vide ≥ 33 %
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x] == ".":
                grid[y][x] = "I"
    labels.append(dict(text="Agout", x=next((x for x in range(COLS) if grid[3][x] == "w"), COLS // 2), y=3))

    def share():
        n = sum(1 for row in grid for c in row if c in OPEN)
        return 100 * n / (COLS * ROWS)

    def cut_blocks(limit):
        cuts = 0
        for _ in range(60):
            big = [c for c in components(grid, "I", protected) if max(bbox_of(c)[2:]) > limit]
            if not big:
                break
            for cells in big:
                x, y, w, h = bbox_of(cells)
                cs = set(cells)
                if w >= h:
                    xm = x + w // 2 - INNER_W // 2
                    for (cx, cy) in cells:
                        if xm <= cx < xm + INNER_W:
                            grid[cy][cx] = "r"
                else:
                    ym = y + h // 2 - INNER_W // 2
                    for (cx, cy) in cells:
                        if ym <= cy < ym + INNER_W:
                            grid[cy][cx] = "r"
                cuts += 1
        return cuts

    def clean_slivers():
        n = 0
        for cells in components(grid, "I", protected):
            x, y, w, h = bbox_of(cells)
            if min(w, h) < 3 or len(cells) < 9:
                for cx, cy in cells:
                    grid[cy][cx] = "r"
                n += 1
        return n

    limit = max_block
    while True:
        cuts = cut_blocks(limit)
        sl = clean_slivers()
        s = share()
        say(f"découpe des îlots > {limit} cases : {cuts} coupe(s), {sl} éclat(s) absorbé(s) → rues + places + parcs = {s:.1f} %")
        if s >= TARGET_SHARE or limit <= 6:
            break
        limit -= 2
    say(f"part rues + places + parcs : {s:.1f} % (objectif ≥ {TARGET_SHARE:.0f} %), îlots ≤ {limit} cases de côté")

    layout = dict(cols=COLS, rows=ROWS, cell_cm=1.0, cells="\n".join("".join(r) for r in grid),
                  legend=LEGEND, monuments=monuments, labels=labels,
                  background=dict(x=0, y=0, w=COLS, opacity=0.5, name="fond_castres_grille.png"),
                  meta=dict(factor=round(g.f, 4), bbox=dict(south=g.s, west=g.w, north=g.n, east=g.e),
                            max_block=limit, open_share=round(s, 1), source=os.path.basename(osm_path)))
    return layout, g, log


# ---------------------------------------------------------------------------
# PNG de contrôle
# ---------------------------------------------------------------------------
def preview(layout, path, log, cell=20, margin=70):
    W, H = COLS * cell + 2 * margin, ROWS * cell + 2 * margin + 60
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    rows = layout["cells"].split("\n")
    ox, oy = margin, margin + 60
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            d.rectangle([ox + x * cell, oy + y * cell, ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1], fill=COLORS[c])
    for x in range(COLS + 1):
        d.line([ox + x * cell, oy, ox + x * cell, oy + ROWS * cell], fill=(0, 0, 0, 40) if x % 15 else (0, 0, 0), width=1)
    for y in range(ROWS + 1):
        d.line([ox, oy + y * cell, ox + COLS * cell, oy + y * cell], fill=(0, 0, 0, 40), width=1)
    for i in range(8):
        x = ox + round(i * COLS / 7) * cell
        d.line([x, oy, x, oy + ROWS * cell], fill=(0, 0, 0), width=3)
    for j in range(5):
        y = oy + round(j * ROWS / 4) * cell
        d.line([ox, y, ox + COLS * cell, y], fill=(0, 0, 0), width=3)
    big = fond.load_font(30); small = fond.load_font(16)
    for i, L in enumerate("ABCDEFG"):
        d.text((ox + (i + .5) * COLS / 7 * cell, oy - 24), L, fill=(0, 0, 0), font=big, anchor="mm")
    for j, L in enumerate("1234"):
        d.text((ox - 30, oy + (j + .5) * ROWS / 4 * cell), L, fill=(0, 0, 0), font=big, anchor="mm")
    for m in layout["monuments"]:
        x0, y0 = ox + m["x"] * cell, oy + m["y"] * cell
        x1, y1 = x0 + m["w"] * cell, y0 + m["h"] * cell
        for k in range(-m["h"] * cell, m["w"] * cell, cell):
            xa, xb = x0 + k, x0 + k + m["h"] * cell
            ya, yb = y0, y1
            # tronquer la hachure au rectangle
            if xa < x0:
                ya = y0 + (x0 - xa); xa = x0
            if xb > x1:
                yb = y1 - (xb - x1); xb = x1
            if xb > xa:
                d.line([xa, ya, xb, yb], fill=(0, 0, 0), width=1)
        d.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=3)
        d.text((x0 + 4, y0 + 2), m["id"], fill=(0, 0, 0), font=small)
    for l in layout["labels"]:
        x, y = ox + (l["x"] + .5) * cell, oy + (l["y"] + .5) * cell
        tw = d.textlength(l["text"], font=small)
        d.rectangle([x - 3, y - 10, x + tw + 3, y + 10], fill=(255, 255, 255))
        d.text((x, y), l["text"], fill=(31, 95, 191), font=small, anchor="lm")
    meta = layout["meta"]
    d.text((margin, 14), f"MicroMacro-Castres — brouillon 00_osm_to_layout.py — facteur {meta['factor']} case/m "
           f"(1 case = {1 / meta['factor']:.1f} m) — rues + places + parcs {meta['open_share']} % (objectif ≥ 33 %) — îlots ≤ {meta['max_block']} cases",
           fill=(0, 0, 0), font=fond.load_font(22))
    lx = margin
    for c, name in LEGEND.items():
        d.rectangle([lx, 44, lx + 18, 62], fill=COLORS[c], outline=(0, 0, 0))
        d.text((lx + 24, 53), f"{c} {name}", fill=(0, 0, 0), font=small, anchor="lm")
        lx += 110
    d.text((lx + 10, 53), "monuments hachurés", fill=(0, 0, 0), font=small, anchor="lm")
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/castres.osm")
    ap.add_argument("--out", default="data/layout.json")
    ap.add_argument("--preview", default="out/layout_preview.png")
    ap.add_argument("--fond", default="data/fond_castres_grille.png", help="fond recadré sur la grille ('' pour ne pas le produire)")
    ap.add_argument("--max-block", type=int, default=12)
    a = ap.parse_args()
    layout, g, log = build(a.osm, a.max_block)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    print(f"écrit {a.out}")
    if a.preview:
        os.makedirs(os.path.dirname(a.preview) or ".", exist_ok=True)
        preview(layout, a.preview, log)
        print(f"écrit {a.preview}")
    if a.fond:
        fond.render(a.osm, a.fond, g.bbox(), COLS * 20)
        print(f"écrit {a.fond} (fond aligné sur la grille : x = 0, y = 0, largeur = {COLS} cases)")


if __name__ == "__main__":
    main()
