#!/usr/bin/env python3
"""
00_osm_to_layout.py — Fiche 002, partie A : brouillon automatique du plan de
jeu à partir de data/castres.osm.

Ce que fait le script, dans l'ordre (voir tasks/002_layout_editor.md) :
  1. pose la grille 71 × 106 (portrait) sur le cœur de DECISIONS.md : centre,
     angle -5,5°, facteur 0,17 case/m (1 case ≈ 5,9 m)
  2. garde tout le réseau réel (rues, ruelles, venelles, passages, escaliers,
     allées) avec ses connexions ; largeur selon le caractère (venelle 1,
     ruelle 2, rue 3, rue nommée 4, boulevard / quai 6) ; redressement
     orthogonal sans escalier de cases (un coude au plus toutes les 8 cases)
  3. pose l'eau (Agout élargi à ≥ 8 cases), les quais (2 cases), la place
     Jean-Jaurès (18 × 8), le jardin de l'Évêché, les autres parcs
  4. réserve les rectangles des monuments de DECISIONS.md (position OSM,
     décalages explicites)
  5. tout le reste devient îlot, plein ; le vide n'est qu'une information
  6. écrit data/layout.json, data/fond_castres_grille.png (fond recadré sur
     la grille pour l'éditeur) et out/layout_preview.png (PNG de contrôle)

Usage :
  python3 pipeline/00_osm_to_layout.py
  python3 pipeline/00_osm_to_layout.py --osm data/castres.osm --out data/layout.json \
      --preview out/layout_preview.png --rotate auto

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
COLS, ROWS = 71, 106      # portrait, comme la carte MicroMacro posée sur la table (papier 75 × 110 cm)
# Repère de référence : centre de l'ancien périmètre étendu (les décalages du
# cœur sont exprimés en mètres tournés par rapport à ce point).
REF = dict(south=43.6010, west=2.2335, north=43.6076, east=2.2450)
# Cœur (décision du 17/09) : rectangle 71 × 106 cases (418 × 624 m à 0,17)
# posé sur le centre-ville, défini par son centre (du, dv en mètres tournés
# depuis REF), l'angle de la grille et le facteur (cases par mètre). Centré sur
# les neuf éléments obligatoires (u 114–513, v −233–273 → 313, 20), puis
# décalé de 20 m vers l'ouest pour prendre la rue Chambre de l'Édit. Voir
# DECISIONS.md.
CORE = dict(du=293.0, dv=20.0, angle=-5.5, factor=0.170)
# Repères imprimés en marge : lettres sur le grand côté, chiffres sur le petit
BANDS_X, BANDS_Y = ("1234", "ABCDEFG") if COLS < ROWS else ("ABCDEFG", "1234")

# Règles du 16/09 :
#  1. tout le réseau réel est gardé (rues, ruelles, venelles, passages,
#     escaliers, allées), avec ses connexions ; aucune voie supprimée
#  2. largeur selon le caractère : venelle 1, ruelle 2, rue 3, rue nommée 4,
#     boulevard / quai 6 (lettre 'b', plantés) ; pas d'escalier de cases :
#     au plus un coude à angle droit toutes les MIN_RUN cases
#  3. tout ce qui n'est ni voie, ni place, ni parc, ni eau est îlot, plein
#  4. le vide n'est qu'une information
# Largeurs du 17/09 : venelle 1, rue ordinaire (et ruelle) 2, avenue / voie
# primaire 3, cinq rues nommées de DECISIONS 4, boulevards Léon Bourgeois /
# Miredames / Henri Sizaire et quais 5
VENELLE_W, RUE_W, AVENUE_W, STREET_W, BOULEVARD_W = 1, 2, 3, 4, 5
QUAI_RES_W = 5           # quais résidentiels (Tourcaudière, du Carras, du Moulin…) : 5 = règle « quais 5 », 2 = largeur réelle
MIN_RUN, BAND = 8, 2.0
NAMED_STREETS = [r"Rue Sabatier$", r"Rue Frédéric Thomas", r"Rue Victor Hugo", r"Rue de l'Hôtel de Ville",
                 r"Rue Villegoudou", r"Quai des Jacobins", r"^Pont Vieux", r"^Pont Neuf"]
SKIP_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "track", "bus_stop", "platform",
                "proposed", "construction", "raceway", "elevator"}

WATER_MIN_W = 6          # cases : à 0,17 l'Agout fait 6 cases à sa largeur réelle ; on ne l'élargit pas
QUAI_W = 2

OPEN = "rbpP"

# Monuments (règles du 17/09) : emprise réelle OSM compressée, agrandie de
# MONUMENT_GROW (30 % en surface) dans les îlots voisins uniquement, jamais sur
# une voie. Une voie ne traverse pas un monument : les venelles et ruelles qui
# tombent sous l'emprise réelle disparaissent, les autres voies sont repoussées
# au bord. Les ponts sont des voies ; les maisons sur l'Agout sont les bâtiments
# OSM de la rive gauche entre les deux ponts.
MONUMENT_GROW = 0.30
MONUMENTS = [            # id, regex sur le nom OSM, lettre, niveaux
    ("saint-benoit", r"Cathédrale Saint-Beno[iî]t", "I", 3),
    ("eveche-mairie", r"Hôtel de Ville de Castres|Musée Goya", "I", 3),   # palais de l'Évêché = hôtel de ville + musée Goya
    ("jardin-eveche", r"Jardin de l'?[ÉE]v[êe]ch[ée]", "P", 0),
    ("theatre", r"Théâtre [Mm]unicipal", "I", 3),
    ("saint-jacques", r"^Église Saint-Jacques", "I", 3),
]
ALIGN_TOLERANCE = 20     # ° : un élément qui s'écarte de plus que ça des autres est signalé et ignoré

# Rotation de la grille : éléments qui doivent être droits (le cœur) ; les
# boulevards ont le droit d'être en escalier.
ALIGN_ON = [r"Place Jean[- ]Jaur[èe]s", r"^Rue Sabatier$", r"^Rue Victor Hugo$"]

COLORS = {"r": (227, 227, 227), "b": (205, 214, 196), "I": (201, 162, 126), "m": (166, 118, 80), "p": (243, 214, 107),
          "P": (159, 211, 155), "w": (142, 193, 230), "q": (220, 205, 176), ".": (255, 255, 255)}
LEGEND = {"r": "rue", "b": "boulevard", "I": "ilot", "m": "maison", "p": "place", "P": "parc", "w": "eau", "q": "quai", ".": "vide"}


# ---------------------------------------------------------------------------
# Projection périmètre → grille
# ---------------------------------------------------------------------------
class Grid:
    """Grille COLS × ROWS définie par son centre géographique, son angle (sens
    trigonométrique, nord en haut) et son facteur (cases par mètre). Le centre
    de la grille est la case (COLS/2, ROWS/2)."""

    def __init__(self, ref=REF, angle=0.0, factor=None, du=0.0, dv=0.0):
        self.rlat, self.rlon = (ref["south"] + ref["north"]) / 2, (ref["west"] + ref["east"]) / 2
        self.kx = 111320 * math.cos(math.radians(self.rlat))
        self.ky = 111320
        self.angle = angle
        self.cos, self.sin = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        # centre de la grille : (du, dv) en mètres tournés depuis le point de référence
        mx = du * self.cos - dv * self.sin
        my = du * self.sin + dv * self.cos
        self.clat, self.clon = self.rlat + my / self.ky, self.rlon + mx / self.kx
        self.f = factor if factor else ROWS / ((ref["north"] - ref["south"]) * self.ky)
        self.cx, self.cy = COLS / 2, ROWS / 2
        self.w_m, self.h_m = COLS / self.f, ROWS / self.f

    def meters(self, latlon):
        lat, lon = latlon
        return ((lon - self.clon) * self.kx, (lat - self.clat) * self.ky)   # est, nord depuis le centre

    def rotated(self, latlon):
        mx, my = self.meters(latlon)
        return (mx * self.cos + my * self.sin, -mx * self.sin + my * self.cos)

    def cell(self, latlon):
        """Coordonnées continues en cases (x vers la droite, y vers le bas)."""
        u, v = self.rotated(latlon)
        return (u * self.f + self.cx, -v * self.f + self.cy)

    def corners(self):
        """Les quatre coins de la grille en (lat, lon), dans l'ordre NW, NE, SE, SW."""
        out = []
        for u, v in ((-self.w_m / 2, self.h_m / 2), (self.w_m / 2, self.h_m / 2), (self.w_m / 2, -self.h_m / 2), (-self.w_m / 2, -self.h_m / 2)):
            mx = u * self.cos - v * self.sin; my = u * self.sin + v * self.cos
            out.append((round(self.clat + my / self.ky, 6), round(self.clon + mx / self.kx, 6)))
        return out

    def bbox(self):
        """bbox géographique de la grille non tournée (fond de l'éditeur)."""
        w = self.clon - self.w_m / 2 / self.kx
        e = self.clon + self.w_m / 2 / self.kx
        return (self.clat - self.h_m / 2 / self.ky, w, self.clat + self.h_m / 2 / self.ky, e)


def angle_of_polyline(pts):
    """Orientation dominante (degrés, modulo 90, dans ]-45, 45]) d'une polyligne
    en mètres, pondérée par la longueur : moyenne circulaire de 4·φ."""
    sx = sy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L == 0:
            continue
        a = 4 * math.atan2(y1 - y0, x1 - x0)
        sx += L * math.cos(a); sy += L * math.sin(a)
    return math.degrees(math.atan2(sy, sx)) / 4 if (sx or sy) else 0.0


def mean_angle(angles):
    sx = sum(math.cos(math.radians(4 * a)) for a in angles)
    sy = sum(math.sin(math.radians(4 * a)) for a in angles)
    return math.degrees(math.atan2(sy, sx)) / 4


def auto_angle(nodes, ways, g):
    """Angle qui rend droits les éléments de ALIGN_ON (place : grand axe par
    ACP des sommets ; rues : orientation pondérée par la longueur)."""
    found = []
    for pat in ALIGN_ON:
        rx = re.compile(pat)
        pts_all = []
        for way in ways.values():
            name = way["tags"].get("name", "")
            if not rx.search(name):
                continue
            pts = [g.meters(nodes[n]) for n in way["nodes"] if n in nodes]
            if len(pts) >= 2:
                pts_all.append((name, pts, way["tags"]))
        if not pts_all:
            print(f"ATTENTION : rien ne correspond à {pat} pour l'alignement")
            continue
        if pat.startswith("Place"):
            pts = [p for _, ps, _ in pts_all for p in ps]
            mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
            sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts)
            sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
            a = math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy))
        else:
            a = mean_angle([angle_of_polyline(ps) for _, ps, _ in pts_all if len(ps) >= 2])
        a = ((a + 45) % 90) - 45
        found.append((pat, a))
    # les éléments concordants font la moyenne ; un élément à plus de
    # ALIGN_TOLERANCE degrés des autres (typiquement à 45°) est exclu et signalé
    kept = list(found)
    excluded = []
    while len(kept) > 1:
        m = mean_angle([a for _, a in kept])
        dev = [(abs(((a - m + 45) % 90) - 45), pat, a) for pat, a in kept]
        worst = max(dev)
        if worst[0] <= ALIGN_TOLERANCE:
            break
        excluded.append((worst[1], worst[2], m))
        kept = [(pat, a) for pat, a in kept if pat != worst[1]]
    theta = mean_angle([a for _, a in kept]) if kept else 0.0
    theta = ((theta + 45) % 90) - 45
    return theta, found, excluded


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


def merge_streets(streets):
    """Regroupe les tronçons OSM d'une même rue en une polyligne, en chaînant
    les tronçons qui partagent un nœud d'extrémité. S'il reste plusieurs
    chaînes (rue interrompue), on garde la plus longue."""
    by_name = {}
    for st in streets:
        by_name.setdefault(st["name"], []).append(st)
    merged = []
    for name, segs in by_name.items():
        segs = [dict(s) for s in segs if len(s["nodes"]) >= 2]
        chains = []
        while segs:
            cur = segs.pop(0)
            nodes, pts = list(cur["nodes"]), list(cur["pts"])
            changed = True
            while changed:
                changed = False
                for i, o in enumerate(segs):
                    if o["nodes"][0] == nodes[-1]:
                        nodes += o["nodes"][1:]; pts += o["pts"][1:]
                    elif o["nodes"][-1] == nodes[-1]:
                        nodes += o["nodes"][-2::-1]; pts += o["pts"][-2::-1]
                    elif o["nodes"][-1] == nodes[0]:
                        nodes = o["nodes"][:-1] + nodes; pts = o["pts"][:-1] + pts
                    elif o["nodes"][0] == nodes[0]:
                        nodes = o["nodes"][::-1][:-1] + nodes; pts = o["pts"][::-1][:-1] + pts
                    else:
                        continue
                    segs.pop(i); changed = True
                    break
            L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            chains.append((L, pts))
        chains.sort(key=lambda c: -c[0])
        best = chains[0]
        merged.append(dict(name=name, pts=best[1], w=segs and 0 or by_name[name][0]["w"],
                           bridge=by_name[name][0]["bridge"], fragments=len(chains) - 1,
                           length=best[0]))
    return merged


def _dist_to_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def fit_two_segments(pts, tol):
    """Règle 1 : redresse une polyligne (cases continues) en une droite ou un L
    (deux segments à angle droit). Renvoie (forme, segments, écart) ou None si
    l'écart maximal dépasse tol. Les segments sont en cases entières."""
    n = len(pts)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    best = None
    # droite horizontale ou verticale
    for horiz in (True, False):
        if horiz:
            c = sum(ys) / n; a, b = (min(xs), c), (max(xs), c)
        else:
            c = sum(xs) / n; a, b = (c, min(ys)), (c, max(ys))
        dev = max(_dist_to_segment(p, a, b) for p in pts)
        if best is None or dev < best[2]:
            best = ("droite", [(a, b)], dev)
    if best[2] <= FIT_TOL_STREET:
        form, segs, dev = best                  # une droite suffit
    else:
        # L : coupure en k, première jambe sur un axe, seconde sur l'autre ;
        # on garde le meilleur des deux (droite ou L), puis on applique tol
        bestL = None
        for k in range(1, n - 1):
            for first_h in (True, False):
                p1, p2 = pts[:k + 1], pts[k:]
                if first_h:
                    y1 = sum(p[1] for p in p1) / len(p1); x2 = sum(p[0] for p in p2) / len(p2)
                    corner = (x2, y1)
                    a, b = (pts[0][0], y1), (x2, pts[-1][1])
                else:
                    x1 = sum(p[0] for p in p1) / len(p1); y2 = sum(p[1] for p in p2) / len(p2)
                    corner = (x1, y2)
                    a, b = (x1, pts[0][1]), (pts[-1][0], y2)
                dev = max(min(_dist_to_segment(p, a, corner), _dist_to_segment(p, corner, b)) for p in pts)
                if bestL is None or dev < bestL[2]:
                    bestL = ("L", [(a, corner), (corner, b)], dev)
        if bestL is not None and bestL[2] < best[2]:
            best = bestL
        if best[2] > tol:
            return None
        form, segs, dev = best
    rounded = [((int(round(a[0])), int(round(a[1]))), (int(round(b[0])), int(round(b[1])))) for a, b in segs]
    # un segment doit être strictement axial après arrondi
    fixed = []
    for (ax, ay), (bx, by) in rounded:
        if ax != bx and ay != by:
            if abs(bx - ax) >= abs(by - ay):
                by = ay
            else:
                bx = ax
        fixed.append(((ax, ay), (bx, by)))
    if form == "L":   # recoller la seconde jambe au coin arrondi
        (a0, c0), (c1, b1) = fixed
        c1 = c0
        if c1[0] != b1[0] and c1[1] != b1[1]:
            b1 = (c1[0], b1[1]) if abs(b1[1] - c1[1]) >= abs(b1[0] - c1[0]) else (b1[0], c1[1])
        fixed = [(a0, c0), (c1, b1)]
    return form, fixed, dev


def stamped_cells(a, b, w):
    """Cases couvertes par un segment axial d'épaisseur w (sans les écrire)."""
    (x0, y0), (x1, y1) = a, b
    lo = -(w // 2); hi = lo + w
    out = []
    if y0 == y1:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for d in range(lo, hi):
                if inside(x, y0 + d):
                    out.append((x, y0 + d))
    else:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for d in range(lo, hi):
                if inside(x0 + d, y):
                    out.append((x0 + d, y))
    return out


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
# ---------------------------------------------------------------------------
# Réseau réel (règles du 16/09) : classement et largeur des voies
# ---------------------------------------------------------------------------
BIG_BOULEVARDS = [r"Boulevard Léon Bourgeois", r"Boulevard Miredames", r"Boulevard Henri Sizaire"]
# Exceptions de largeur (décision du 17/09, soir) : le quai des Jacobins n'est
# qu'un passage entre la façade est de la place Jean-Jaurès et les Arcades,
# les maisons sur l'Agout ; il fait 2 cases, pas 5
WIDTH_EXCEPTIONS = {r"^Quai des Jacobins": 2}


def classify(tags, name):
    """Caractère de la voie → dict(w, ch, kind, named) ou (None, raison) si la
    voie est écartée d'office (règle 1) :
    venelle 1, ruelle 2, rue 3, rue nommée / avenue / voie primaire 4,
    boulevards Léon Bourgeois, Miredames, Henri Sizaire et quais 6 ('b')."""
    hw = tags.get("highway")
    if hw in SKIP_CLASSES or hw is None:
        return None, f"highway={hw}"
    if hw == "footway" and tags.get("footway") in ("sidewalk", "crossing"):
        return None, f"footway={tags.get('footway')} (trottoir / passage piéton)"
    if hw == "service" and not name:
        return None, "service non nommée (accès, parking, livraison)"
    if hw in ("path", "cycleway"):
        return None, f"highway={hw}"
    if hw == "steps" and not name:
        return None, "escalier non nommé"
    first = name.split(" ")[0] if name else ""
    named = any(re.compile(p).search(name) for p in NAMED_STREETS)
    for pat, w_ in WIDTH_EXCEPTIONS.items():
        if re.compile(pat).search(name):
            return dict(w=w_, ch="r", kind=f"exception {w_}", named=True), None
    if any(re.compile(p).search(name) for p in BIG_BOULEVARDS) or (first == "Quai" and hw in ("primary", "secondary", "tertiary")):
        return dict(w=BOULEVARD_W, ch="b", kind=f"boulevard / quai {BOULEVARD_W}", named=True), None
    if first == "Quai":
        # quai résidentiel (rue de 8 m le long de l'eau) : largeur QUAI_RES_W
        return dict(w=QUAI_RES_W, ch="b" if QUAI_RES_W >= 4 else "r", kind=f"quai résidentiel {QUAI_RES_W}", named=True), None
    if named:
        return dict(w=STREET_W, ch="r", kind=f"rue nommée {STREET_W}", named=True), None
    if first in ("Boulevard", "Avenue", "Allées") or hw in ("primary", "secondary", "primary_link", "secondary_link"):
        return dict(w=AVENUE_W, ch="r", kind=f"avenue / voie primaire {AVENUE_W}", named=bool(name)), None
    if first in ("Venelle", "Passage", "Escalier", "Rampe") or hw in ("footway", "steps"):
        return dict(w=VENELLE_W, ch="r", kind=f"venelle {VENELLE_W}", named=bool(name)), None
    if first in ("Ruelle", "Impasse") or hw in ("living_street", "service"):
        return dict(w=RUE_W, ch="r", kind=f"ruelle {RUE_W}", named=bool(name)), None
    return dict(w=RUE_W, ch="r", kind=f"rue {RUE_W}", named=bool(name)), None


def rectify_manhattan(pts, min_run=8, band=2.0):
    """Règle 2 : polyligne (cases continues) → chemin orthogonal sans escalier
    de cases. Chaque tronçon droit fait au moins min_run cases, sauf le dernier ;
    on reste droit tant que le tracé réel s'écarte de moins de `band` cases, et
    quand le tracé est oblique on fait des marches d'au moins min_run.
    Renvoie une liste de segments axiaux en cases entières, connectés, qui
    partent du premier point réel et arrivent au dernier."""
    P = [(round(x), round(y)) for x, y in pts]
    P = [p for i, p in enumerate(P) if i == 0 or p != P[i - 1]]
    if len(P) == 1:
        return [(P[0], P[0])]
    segs = []
    cur = P[0]
    i = 0
    n = len(P)
    # direction initiale : celle du premier déplacement dominant
    dx, dy = P[-1][0] - P[0][0], P[-1][1] - P[0][1]
    for k in range(1, n):
        if abs(P[k][0] - P[0][0]) >= min_run or abs(P[k][1] - P[0][1]) >= min_run:
            dx, dy = P[k][0] - P[0][0], P[k][1] - P[0][1]
            break
    horiz = abs(dx) >= abs(dy)
    guard = 0
    while i < n - 1 and guard < 400:
        guard += 1
        # jusqu'où peut-on rester droit dans la direction courante ?
        j = i + 1
        while j < n - 1:
            dev = abs(P[j][1] - cur[1]) if horiz else abs(P[j][0] - cur[0])
            if dev > band:
                break
            j += 1
        # longueur de la course : au moins min_run (sauf si la fin est proche)
        target = P[j]
        run = abs(target[0] - cur[0]) if horiz else abs(target[1] - cur[1])
        if run < min_run and j < n - 1:
            # avancer jusqu'à un point qui donne une course de min_run
            jj = j
            while jj < n - 1 and (abs(P[jj][0] - cur[0]) if horiz else abs(P[jj][1] - cur[1])) < min_run:
                jj += 1
            j = jj; target = P[j]
        if horiz:
            nxt = (target[0], cur[1])
        else:
            nxt = (cur[0], target[1])
        if nxt != cur:
            segs.append((cur, nxt)); cur = nxt
        i = j
        if i >= n - 1:
            break
        horiz = not horiz
    # raccord final vers le dernier point réel (un L au plus)
    last = P[-1]
    if cur != last:
        if horiz:
            mid = (last[0], cur[1])
        else:
            mid = (cur[0], last[1])
        if mid != cur:
            segs.append((cur, mid))
        if mid != last:
            segs.append((mid, last))
    return segs


def collect(parsed, g):
    """Lit l'OSM projeté : toutes les voies (règle 1), l'eau, les parcs, la place
    et le jardin, les éléments nommés (monuments)."""
    nodes, ways, rels = parsed

    def coords(way):
        return [g.cell(nodes[n]) for n in way["nodes"] if n in nodes]

    streets, water, parks, place, jardin = [], [], [], [], []
    dropped = []               # (nom ou type, raison) — règle 1
    features = {}
    for wid, way in ways.items():
        t = way["tags"]
        name = t.get("name", "")
        hw = t.get("highway")
        pts = coords(way)
        closed = len(way["nodes"]) > 3 and way["nodes"][0] == way["nodes"][-1]
        is_area = t.get("area") == "yes" or (hw == "pedestrian" and closed)
        if hw and not is_area and len(pts) >= 2 and any(-2 <= p[0] < COLS + 2 and -2 <= p[1] < ROWS + 2 for p in pts):
            c, why = classify(t, name)
            label = name or f"({hw} sans nom)"
            if c is None:
                dropped.append((label, why))
            else:
                streets.append(dict(id=wid, name=name, label=label, hw=hw, pts=pts,
                                    nodes=[n for n in way["nodes"] if n in nodes], **c,
                                    bridge=t.get("bridge") == "yes" or name.startswith("Pont ")))
        if closed and len(pts) >= 4:
            if t.get("natural") == "water" or t.get("water") in ("river", "canal") or t.get("waterway") == "riverbank":
                water.append(pts)
            elif t.get("leisure") in ("park", "garden"):
                (jardin if re.search(r"Jardin de l'?[ÉE]v[êe]ch[ée]", name) else parks).append(pts)
            elif re.search(r"Place Jean[- ]Jaur[èe]s", name) and (t.get("place") == "square" or is_area):
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
    return streets, water, parks, place, jardin, features, nodes, dropped


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


def line_cells(a, b):
    (x0, y0), (x1, y1) = a, b
    if y0 == y1:
        return [(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)]
    return [(x0, y) for y in range(min(y0, y1), max(y0, y1) + 1)]


# ---------------------------------------------------------------------------
# Construction du brouillon
# ---------------------------------------------------------------------------
def build(osm_path, rotate=None, core=None, verbose=True):
    log = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        log.append(s)
        if verbose:
            print(s)

    parsed = fond.parse_osm(osm_path)
    core = dict(CORE, **(core or {}))
    if rotate == "auto":
        theta, found, excluded = auto_angle(parsed[0], parsed[1], Grid(REF, 0.0))
        for pat, a in found:
            say(f"orientation de {pat} : {a:+.1f}° (modulo 90)")
        for pat, a, m in excluded:
            say(f"ATTENTION : {pat} ({a:+.1f}°) est à {abs(((a - m + 45) % 90) - 45):.0f}° des autres : ignoré")
        say(f"rotation retenue : {theta:+.2f}°")
        core["angle"] = theta
    elif rotate is not None:
        core["angle"] = float(rotate)
    g = Grid(REF, core["angle"], core["factor"], core["du"], core["dv"])
    say(f"cœur : centre ({core['du']:+.0f}, {core['dv']:+.0f}) m depuis le repère, grille {g.w_m:.0f} × {g.h_m:.0f} m, "
        f"facteur {g.f:.3f} case/m (1 case = {1 / g.f:.1f} m), tournée de {g.angle:+.2f}°")
    streets, water, parks, place, jardin, features, nodes, dropped = collect(parsed, g)
    from collections import Counter
    kinds = Counter(st["kind"] for st in streets)
    say(f"OSM : {len(streets) + len(dropped)} voies dans la grille ; {len(dropped)} écartées d'office (règle 1), "
        f"{len(streets)} candidates — " + ", ".join(f"{n} × {k}" for k, n in sorted(kinds.items())))

    grid = [["."] * COLS for _ in range(ROWS)]
    protected = [[False] * COLS for _ in range(ROWS)]
    monuments, labels = [], []

    # 1. eau, élargie à WATER_MIN_W, puis quais
    for ring in water:
        fill_polygon(grid, ring, "w")
    widths = [sum(1 for x in range(COLS) if grid[y][x] == "w") for y in range(ROWS)]
    widths = [w for w in widths if w]
    med = sorted(widths)[len(widths) // 2] if widths else 0
    grow = max(0, math.ceil((WATER_MIN_W - med) / 2))
    dilate(grid, "w", "w", grow)
    say(f"Agout : largeur médiane {med} cases → dilatation {grow} → ≥ {med + 2 * grow}")
    dilate(grid, "w", "q", QUAI_W)
    river = [[grid[y][x] in "wq" for x in range(COLS)] for y in range(ROWS)]   # figé avant les voies

    # 2. parcs (polygones réels), place (rectangle fixe, 4 cases de la rive)
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
        x, y = max(0, int(round(min(xs)))), max(0, int(round(min(ys))))
        w, h = min(COLS - x, int(round(max(xs))) - x), min(ROWS - y, int(round(max(ys))) - y)
        place_rect = (x, y, w, h)
        say(f"place Jean-Jaurès : emprise réelle {w} × {h} cases en {x},{y}")
    else:
        say("ATTENTION : place Jean-Jaurès introuvable dans l'OSM")

    # 3. voies : redressement orthogonal (un coude au plus toutes les MIN_RUN
    #    cases), doublons de trottoir écartés, îlots < 4 cases résorbés en
    #    supprimant la voie non nommée la moins importante, connexions vérifiées
    for st in streets:
        st["decisions"] = st["named"] and st["kind"].startswith(("rue nommée", "boulevard"))
        st["segs"] = rectify_manhattan(st["pts"], MIN_RUN, BAND)
        st["axis"] = [c for a, b in st["segs"] for c in line_cells(a, b)]
        st["axis"] = [c for i_, c in enumerate(st["axis"]) if i_ == 0 or c != st["axis"][i_ - 1]]
        st["cells"] = {c for a, b in st["segs"] for c in stamped_cells(a, b, st["w"])}
    n_bends = sum(max(0, len(st["segs"]) - 1) for st in streets)
    importance = lambda st: (st["w"], len(st["axis"]))       # venelle avant ruelle avant rue, courte avant longue

    # 3a. doublons : voie non nommée qui longe une autre voie à ≤ 2 cases sur plus
    #     de la moitié de sa longueur (trottoir, contre-allée)
    index = {}
    for st in streets:
        for c in st["axis"]:
            index.setdefault(c, set()).add(st["id"])
    active = []
    for st in sorted(streets, key=importance):
        if st["name"]:            # règle 1 : seules les voies sans nom OSM peuvent être des doublons
            active.append(st); continue
        close = 0; others = Counter()
        for (x, y) in st["axis"]:
            near = set()
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    near |= index.get((x + dx, y + dy), set())
            near.discard(st["id"])
            if near:
                close += 1
                for o in near:
                    others[o] += 1
        if st["axis"] and close / len(st["axis"]) > 0.5:
            by_id = {s_["id"]: s_ for s_ in streets}
            twin = by_id[others.most_common(1)[0][0]]
            dropped.append((st["label"], f"doublon de trottoir : longe « {twin['label']} » sur {100 * close // len(st['axis'])} % de sa longueur"))
            for c in st["axis"]:
                index[c].discard(st["id"])
        else:
            active.append(st)
    streets = active

    # 3c. tracé définitif, masque des voies nommées, labels
    named_mask = [[False] * COLS for _ in range(ROWS)]
    center_cells = {}          # id de voie → cases de l'axe
    node_streets = {}          # nœud OSM → ids des voies qui le contiennent
    for st in streets:
        # le long de l'Agout : trottoir (q) ou bâtiments, jamais que la route → les voies ne recouvrent pas la bande de rive
        allow = (lambda x, y: grid[y][x] not in "p") if st["bridge"] else (lambda x, y: grid[y][x] not in "wqp")
        for a, b in st["segs"]:
            stamp_line(grid, a, b, st["w"], st["ch"], allow)
            if st["named"]:
                stamp_line(named_mask, a, b, st["w"], True)
        center_cells[st["id"]] = st["axis"]
        for nd in st["nodes"]:
            node_streets.setdefault(nd, set()).add(st["id"])
        is_decisions = st["decisions"]
        if is_decisions and st["name"] not in [l["text"] for l in labels] and st["axis"]:
            mid = st["axis"][len(st["axis"]) // 2]
            if inside(*mid):
                labels.append(dict(text=st["name"], x=mid[0], y=mid[1]))
    by_id = {st["id"]: st for st in streets}
    connectors = 0
    for nd, ids in node_streets.items():
        if len(ids) < 2 or nd not in nodes:
            continue
        c0 = g.cell(nodes[nd]); c0 = (round(c0[0]), round(c0[1]))
        if not inside(*c0):
            continue
        near = []
        for sid in ids:
            cells = center_cells[sid]
            if cells:
                near.append((sid, min(cells, key=lambda c: (c[0] - c0[0]) ** 2 + (c[1] - c0[1]) ** 2)))
        for (sa, a), (sb, b) in zip(near, near[1:]):
            reach = (by_id[sa]["w"] + by_id[sb]["w"]) / 2 + 1
            if max(abs(a[0] - b[0]), abs(a[1] - b[1])) > reach:
                mid = (b[0], a[1])
                for p_, q_ in ((a, mid), (mid, b)):
                    stamp_line(grid, p_, q_, 1, "r", lambda x, y: grid[y][x] in ".I")
                connectors += 1
    kinds = Counter(st["kind"] for st in streets)
    say(f"voies conservées : {len(streets)} — " + ", ".join(f"{n} × {k}" for k, n in sorted(kinds.items())))
    say(f"voies redressées : {n_bends} coudes au total (≥ {MIN_RUN} cases entre deux coudes), "
        f"{connectors} raccord(s) d'une case ajouté(s) pour garder les connexions réelles")
    reasons = Counter(r.split(" :")[0].split(" (")[0] for _, r in dropped)
    say(f"VOIES SUPPRIMÉES ({len(dropped)}), par raison : " + ", ".join(f"{k} {n}" for k, n in reasons.most_common()))
    log_dropped = [f"{lab} — {why}" for lab, why in dropped]
    # la place est une surface pavée : elle prime sur les voies qui la traversent
    if place_rect:
        x, y, w, h = place_rect
        fill_rect(grid, x, y, w, h, "p", allow=lambda x, y: grid[y][x] not in "wq")
        labels.append(dict(text="Place Jean-Jaurès", x=x + w // 2 - 4, y=y + h // 2))
    share_after_streets = 100 * sum(1 for r in grid for c in r if c in OPEN) / (COLS * ROWS)

    # 4. monuments (règles du 17/09) : emprise réelle OSM compressée ; une voie
    #    ne traverse pas un monument (venelles et ruelles sous l'emprise
    #    disparaissent, les autres voies sont repoussées au bord) ; puis
    #    agrandissement de MONUMENT_GROW dans les îlots voisins, jamais sur une voie
    cell_owner = {}
    for st in streets:
        for c in st["cells"]:
            cell_owner.setdefault(c, []).append(st)
    report = []

    def footprint_cells(rings):
        layer = [["."] * COLS for _ in range(ROWS)]
        for ring in rings:
            fill_polygon(layer, ring, "X")
        return {(x, y) for y in range(ROWS) for x in range(COLS) if layer[y][x] == "X"}

    def place_monument(mid_, rings, ch, levels, label, grow=MONUMENT_GROW, box=True):
        # un monument déjà posé n'est jamais recouvert par le suivant (le jardin entoure le palais)
        F = {c for c in footprint_cells(rings) if grid[c[1]][c[0]] not in "wp" and not protected[c[1]][c[0]]}
        if not F:
            say(f"ATTENTION : {mid_} ← « {label} » : emprise réelle vide dans la grille")
            return None
        real = len(F)
        if ch == "I" and box:
            # un monument bâti est une boîte pleine : le rectangle englobant de
            # l'emprise réelle, élargi côté îlots jusqu'à atteindre +grow en surface
            x0, y0, w, h = bbox_of(list(F))
            x1, y1 = x0 + w - 1, y0 + h - 1

            def box_cells(ax, ay, bx, by):
                return {(x, y) for y in range(ay, by + 1) for x in range(ax, bx + 1)
                        if inside(x, y) and grid[y][x] not in "wp" and not protected[y][x]}
            target = int(round(real * (1 + grow)))
            for _ in range(20):
                if len(box_cells(x0, y0, x1, y1)) >= target:
                    break
                sides = {
                    "w": (x0 - 1, y0, x0 - 1, y1), "e": (x1 + 1, y0, x1 + 1, y1),
                    "n": (x0, y0 - 1, x1, y0 - 1), "s": (x0, y1 + 1, x1, y1 + 1)}
                best = max(sides.items(), key=lambda kv: len([c for c in box_cells(*kv[1]) if grid[c[1]][c[0]] in ".I"]))
                if not box_cells(*best[1]):
                    break
                k = best[0]
                x0, y0, x1, y1 = (x0 - 1 if k == "w" else x0, y0 - 1 if k == "n" else y0, x1 + 1 if k == "e" else x1, y1 + 1 if k == "s" else y1)
                x0, y0, x1, y1 = max(0, x0), max(0, y0), min(COLS - 1, x1), min(ROWS - 1, y1)
            F = box_cells(x0, y0, x1, y1)
            grow = 0.0          # la boîte contient déjà l'agrandissement
        # voies sous l'emprise réelle
        gone, pushed = set(), 0
        for c in F:
            if grid[c[1]][c[0]] in "rb":
                for st in cell_owner.get(c, []):
                    if st["w"] <= RUE_W and st["kind"].startswith(("venelle", "ruelle")):
                        gone.add(st["label"])
                    else:
                        # repoussée au bord : la case la plus proche hors emprise, non-voie
                        best = None
                        for d in range(1, 12):
                            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                                n = (c[0] + dx, c[1] + dy)
                                if inside(*n) and n not in F and grid[n[1]][n[0]] in ".I":
                                    best = n; break
                            if best:
                                break
                        if best:
                            grid[best[1]][best[0]] = st["ch"]; pushed += 1
        for x, y in F:
            grid[y][x] = ch; protected[y][x] = True
        # agrandissement de grow (surface) dans les cases voisines non-voie
        target = int(round(len(F) * grow))
        added = set()
        while len(added) < target:
            ring_ = {}
            for x, y in F | added:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if inside(*n) and n not in F and n not in added and grid[n[1]][n[0]] in ".I" and not protected[n[1]][n[0]]:
                        ring_[n] = ring_.get(n, 0) + 1
            if not ring_:
                break
            for n, k in sorted(ring_.items(), key=lambda kv: -kv[1]):
                if len(added) >= target:
                    break
                added.add(n)
        for x, y in added:
            grid[y][x] = ch; protected[y][x] = True
        cells = F | added
        x0, y0, w, h = bbox_of(list(cells))
        monuments.append(dict(id=mid_, x=x0, y=y0, w=w, h=h, levels=levels, cells=len(cells)))
        planned = int(round(real * (1 + MONUMENT_GROW))) if ch == "I" else int(round(real * (1 + grow)))
        report.append((mid_, real, planned, len(cells), f"{w} × {h}", len(gone), pushed))
        say(f"monument {mid_} ← « {label} » : emprise réelle {real} cases, prévue {planned}, "
            f"obtenue {len(cells)} (rectangle {w} × {h} en {x0},{y0}) ; {len(gone)} venelle(s)/ruelle(s) supprimée(s), "
            f"{pushed} case(s) de voie repoussée(s)")
        return cells

    def polygons_of(pattern):
        rx = re.compile(pattern)
        out, label = [], None
        for name, items in features.items():
            if not rx.search(name):
                continue
            for pts, closed, t in items:
                if closed and len(pts) >= 4:
                    out.append(pts); label = name
        return out, label

    for mid_, pattern, ch, levels in MONUMENTS:
        rings, label = polygons_of(pattern)
        if not rings:
            say(f"ATTENTION : monument {mid_} ({pattern}) introuvable")
            continue
        place_monument(mid_, rings, ch, levels, label)
    # ponts : bande de rue d'une rive à l'autre
    for pid, pattern in (("pont-vieux", r"^Pont Vieux"), ("pont-neuf", r"^Pont Neuf")):
        c, name = feature_center(features, pattern)
        if not c:
            say(f"ATTENTION : {pid} introuvable (hors du cœur ?)")
            continue
        y = int(round(c[1])); xc = int(round(c[0]))
        if not inside(xc, y):
            say(f"ATTENTION : {pid} hors de la grille")
            continue
        y0 = max(0, min(ROWS - STREET_W, y - STREET_W // 2))
        wet = [x for x in range(COLS) if river[y][x]]
        if wet:
            left = max([x for x in wet if x <= xc] or [min(wet)]); right = min([x for x in wet if x >= xc] or [max(wet)])
            while left - 1 >= 0 and river[y][left - 1]:
                left -= 1
            while right + 1 < COLS and river[y][right + 1]:
                right += 1
            fill_rect(grid, left, y0, right - left + 1, STREET_W, "r")
            monuments.append(dict(id=pid, x=left, y=y0, w=right - left + 1, h=STREET_W, levels=0))
            say(f"monument {pid} ← « {name} » en {left},{y0} ({right - left + 1} × {STREET_W})")
    # maisons sur l'Agout : bâtiments OSM de la rive gauche entre les deux ponts
    ponts = sorted([m for m in monuments if m["id"].startswith("pont-")], key=lambda m: m["y"])
    if len(ponts) == 2:
        y0 = ponts[0]["y"] + ponts[0]["h"]; y1 = ponts[1]["y"]
        banks = {}
        for yy in range(y0, y1):
            b = next((x for x in range(COLS) if river[yy][x]), None)
            if b is not None:
                banks[yy] = b
        rings = []
        for name, items in features.items():
            pass
        for wid, way in parsed[1].items():
            t = way["tags"]
            if "building" not in t or len(way["nodes"]) < 4 or way["nodes"][0] != way["nodes"][-1]:
                continue
            pts = [g.cell(parsed[0][n]) for n in way["nodes"] if n in parsed[0]]
            cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
            yy = int(round(cy))
            if yy in banks and banks[yy] - 5 <= cx < banks[yy]:
                rings.append(pts)
        if rings:
            # rangée de maisons : on garde les emprises réelles (pas de boîte), les pieds dans l'eau
            place_monument("maisons-agout", rings, "I", 3, f"{len(rings)} bâtiments OSM sur la rive gauche entre les ponts", grow=0.0, box=False)
        else:
            say("ATTENTION : aucun bâtiment OSM trouvé sur la rive gauche entre les ponts")

    for m in monuments:
        margin = min(m["x"], m["y"], COLS - m["x"] - m["w"], ROWS - m["y"] - m["h"])
        if margin < 3:
            say(f"ATTENTION : {m['id']} à {margin} case(s) du bord de la grille")
    say("marges au bord (cases) : " + ", ".join(f"{m['id']} {min(m['x'], m['y'], COLS - m['x'] - m['w'], ROWS - m['y'] - m['h'])}" for m in monuments))

    # 5. règle 3 : tout le reste est îlot, rempli à 100 % ; aucune découpe
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x] == ".":
                grid[y][x] = "I"
    labels.append(dict(text="Agout", x=next((x for x in range(COLS) if grid[3][x] == "w"), COLS // 2), y=3))
    comps = components(grid, "I", protected)
    n_small = 0
    for c in comps:
        if min(bbox_of(c)[2:]) < 4:
            for xx, yy in c:
                grid[yy][xx] = "m"
            n_small += 1
    say(f"îlots de moins de 4 cases de côté → maison unique à 2 niveaux (lettre m) : {n_small}")
    comps = components(grid, "I", [[False] * COLS for _ in range(ROWS)])
    sizes = sorted((max(bbox_of(c)[2:]) for c in comps), reverse=True)
    n_total = COLS * ROWS
    n_open = sum(1 for r in grid for c in r if c in OPEN)
    n_land = sum(1 for r in grid for c in r if c != "w")
    share, share_land = 100 * n_open / n_total, 100 * n_open / max(1, n_land)
    say(f"îlots : {len(comps)} composantes, plus grand côté {sizes[0] if sizes else 0} cases, "
        f"{sum(1 for s_ in sizes if s_ > 12)} îlot(s) de plus de 12 cases (information)")
    say(f"vide (voies + place + parcs) : {share:.1f} % de la grille, {share_land:.1f} % hors eau (information)")

    layout = dict(cols=COLS, rows=ROWS, cell_cm=1.0, cells="\n".join("".join(r) for r in grid), dropped=log_dropped,
                  legend=LEGEND, monuments=monuments, labels=labels,
                  background=dict(x=0, y=0, w=COLS, opacity=0.5, name="fond_castres_grille.png"),
                  meta=dict(factor=round(g.f, 4), angle=round(g.angle, 2), center=dict(lat=g.clat, lon=g.clon),
                            bbox=dict(zip(("south", "west", "north", "east"), g.bbox())),
                            streets=len(streets), bends=n_bends, connectors=connectors,
                            core=dict(du=core["du"], dv=core["dv"], angle=round(g.angle, 2), factor=round(g.f, 4),
                                      width_m=round(g.w_m, 1), height_m=round(g.h_m, 1), corners=g.corners()),
                            monument_report=report,
                            open_share=round(share, 1), open_share_land=round(share_land, 1),
                            source=os.path.basename(osm_path)))
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
        d.line([ox + x * cell, oy, ox + x * cell, oy + ROWS * cell], fill=(0, 0, 0, 40), width=1)
    for y in range(ROWS + 1):
        d.line([ox, oy + y * cell, ox + COLS * cell, oy + y * cell], fill=(0, 0, 0, 40), width=1)
    nx, ny = len(BANDS_X), len(BANDS_Y)
    for i in range(nx + 1):
        x = ox + round(i * COLS / nx) * cell
        d.line([x, oy, x, oy + ROWS * cell], fill=(0, 0, 0), width=3)
    for j in range(ny + 1):
        y = oy + round(j * ROWS / ny) * cell
        d.line([ox, y, ox + COLS * cell, y], fill=(0, 0, 0), width=3)
    big = fond.load_font(30); small = fond.load_font(16)
    for i, L in enumerate(BANDS_X):
        d.text((ox + (i + .5) * COLS / nx * cell, oy - 24), L, fill=(0, 0, 0), font=big, anchor="mm")
    for j, L in enumerate(BANDS_Y):
        d.text((ox - 30, oy + (j + .5) * ROWS / ny * cell), L, fill=(0, 0, 0), font=big, anchor="mm")
    used_labels = []
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
        lx_, ly_ = x0 + 4, y0 + 2
        if any(abs(lx_ - ux) < 60 and abs(ly_ - uy) < 20 for ux, uy in used_labels):
            lx_, ly_ = x0 + 4, y1 - 20
        tw_ = d.textlength(m["id"], font=small)
        d.rectangle([lx_ - 2, ly_ - 1, lx_ + tw_ + 2, ly_ + 17], fill=(255, 255, 255))
        d.text((lx_, ly_), m["id"], fill=(0, 0, 0), font=small)
        used_labels.append((lx_, ly_))
    for l in layout["labels"]:
        x, y = ox + (l["x"] + .5) * cell, oy + (l["y"] + .5) * cell
        tw = d.textlength(l["text"], font=small)
        d.rectangle([x - 3, y - 10, x + tw + 3, y + 10], fill=(255, 255, 255))
        d.text((x, y), l["text"], fill=(31, 95, 191), font=small, anchor="lm")
    meta = layout["meta"]
    d.text((margin, 14), f"MicroMacro-Castres — cœur, {COLS} × {ROWS} — {meta['angle']:+.1f}° — {meta['factor']} case/m "
           f"(1 case = {1 / meta['factor']:.1f} m) — {meta['streets']} voies gardées, {meta['bends']} coudes — "
           f"vide {meta['open_share']} % de la grille, {meta['open_share_land']} % hors eau (information)",
           fill=(0, 0, 0), font=fond.load_font(22))
    lx = margin
    for c, name in LEGEND.items():
        d.rectangle([lx, 44, lx + 18, 62], fill=COLORS[c], outline=(0, 0, 0))
        d.text((lx + 24, 53), f"{c} {name}", fill=(0, 0, 0), font=small, anchor="lm")
        lx += 95
    d.text((lx + 10, 53), "monuments hachurés", fill=(0, 0, 0), font=small, anchor="lm")
    img.save(path)


def render_fond(osm_path, out, g, px_per_cell=20):
    """Fond gris recadré sur la grille ; si la grille est tournée, on rend un
    carré plus grand, on le tourne autour du centre du périmètre et on recadre."""
    if abs(g.angle) < 1e-6:
        fond.render(osm_path, out, g.bbox(), COLS * px_per_cell)
        return
    m_per_px = 1 / (g.f * px_per_cell)
    half = math.hypot(COLS, ROWS) / g.f / 2 * 1.05          # demi-diagonale de la grille, en m
    big = (g.clat - half / g.ky, g.clon - half / g.kx, g.clat + half / g.ky, g.clon + half / g.kx)
    tmp = out + ".big.png"
    fond.render(osm_path, tmp, big, int(round(2 * half / m_per_px)))
    img = Image.open(tmp).convert("RGB")
    os.remove(tmp); os.remove(tmp.rsplit(".", 1)[0] + ".json")
    # PIL tourne dans le sens trigonométrique à l'écran ; la grille est tournée
    # de +angle dans le monde, donc l'image doit tourner de -angle
    img = img.rotate(-g.angle, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
    W, H = img.size
    cxp, cyp = W / 2, H / 2                                   # centre du périmètre en pixels
    x0 = cxp - g.cx * px_per_cell; y0 = cyp - g.cy * px_per_cell
    img = img.crop((int(round(x0)), int(round(y0)), int(round(x0)) + COLS * px_per_cell, int(round(y0)) + ROWS * px_per_cell))
    img.save(out)
    with open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(dict(angle=g.angle, center=dict(lat=g.clat, lon=g.clon), px_per_cell=px_per_cell,
                       m_per_px=round(m_per_px, 4), cols=COLS, rows=ROWS), f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/castres.osm")
    ap.add_argument("--out", default="data/layout.json")
    ap.add_argument("--preview", default="out/layout_preview.png")
    ap.add_argument("--fond", default="data/fond_castres_grille.png", help="fond recadré sur la grille ('' pour ne pas le produire)")
    ap.add_argument("--rotate", default=None, help="angle de la grille en degrés, ou 'auto' ; défaut : CORE['angle'] (-5,5°)")
    ap.add_argument("--named-width", type=int, default=None, help="largeur des cinq rues nommées (défaut STREET_W = 4)")
    ap.add_argument("--quai-width", type=int, default=None, help="largeur des quais résidentiels (défaut QUAI_RES_W = 5)")
    ap.add_argument("--core", default=None, help="du,dv,facteur : centre du cœur en mètres tournés depuis le repère, et cases par mètre (défaut : CORE)")
    ap.add_argument("--dropped", default="out/voies_supprimees.txt", help="liste des voies supprimées avec la raison")
    a = ap.parse_args()
    if a.named_width:
        globals()["STREET_W"] = a.named_width
    if a.quai_width:
        globals()["QUAI_RES_W"] = a.quai_width
    core = None
    if a.core:
        du, dv, f_ = (float(x) for x in a.core.split(","))
        core = dict(du=du, dv=dv, factor=f_)
    layout, g, log = build(a.osm, a.rotate, core)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    dropped = layout.pop("dropped")
    if a.dropped:
        os.makedirs(os.path.dirname(a.dropped) or ".", exist_ok=True)
        with open(a.dropped, "w", encoding="utf-8") as f:
            f.write(f"Voies supprimées ({len(dropped)})\n\n" + "\n".join(f"- {d}" for d in dropped) + "\n")
        print(f"écrit {a.dropped} ({len(dropped)} voies)")
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    print(f"écrit {a.out}")
    if a.preview:
        os.makedirs(os.path.dirname(a.preview) or ".", exist_ok=True)
        preview(layout, a.preview, log)
        print(f"écrit {a.preview}")
    if a.fond:
        render_fond(a.osm, a.fond, g)
        print(f"écrit {a.fond} (fond aligné sur la grille : x = 0, y = 0, largeur = {COLS} cases, rotation {g.angle:+.2f}°)")


if __name__ == "__main__":
    main()
