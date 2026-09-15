#!/usr/bin/env python3
"""
00b_osm_to_fond.py — Fabrique l'image de fond de l'éditeur de grille
(data/fond_castres.png) à partir de data/castres.osm, à la place d'une
capture d'écran : rues, bâtiments et rivière en gris clair sur blanc.

Le fond n'est qu'un repère visuel pour corriger le layout à la main ; il
n'entre pas dans le rendu final. Un fichier .json à côté du PNG donne son
géoréférencement (bbox, mètres par pixel) pour que l'éditeur ou le script
00_osm_to_layout.py puissent l'aligner sur la grille.

Usage :
  python3 pipeline/00b_osm_to_fond.py                               # défauts
  python3 pipeline/00b_osm_to_fond.py data/castres.osm data/fond_castres.png
  python3 pipeline/00b_osm_to_fond.py --bbox 43.600,2.232,43.612,2.250 --width 3000

Dépendance : pip install pillow
"""

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

# Gris clairs : le fond doit rester en retrait derrière les couleurs de la grille.
COL_BG = (255, 255, 255)
COL_BUILDING = (190, 190, 190)
COL_STREET = (225, 225, 225)
COL_STREET_EDGE = (200, 200, 200)
COL_WATER = (205, 215, 225)
COL_GREEN = (225, 235, 225)
COL_NAME = (120, 120, 120)

# Largeur des rues en mètres selon leur classe OSM (largeur de dessin, pas
# de généralisation : la vraie largeur MicroMacro se décide en fiche 002).
STREET_WIDTH = {
    "primary": 14, "secondary": 12, "tertiary": 10, "residential": 8,
    "unclassified": 8, "living_street": 7, "pedestrian": 8, "service": 5,
    "footway": 2.5, "path": 2, "steps": 2, "cycleway": 2.5,
}
SKIP_HIGHWAY = {"motorway", "motorway_link", "trunk", "trunk_link",
                "proposed", "construction", "platform", "bus_stop"}


def parse_osm(path):
    nodes, ways, rels = {}, {}, {}
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")))
        elif el.tag == "way":
            ways[el.get("id")] = {
                "nodes": [nd.get("ref") for nd in el.findall("nd")],
                "tags": {t.get("k"): t.get("v") for t in el.findall("tag")},
            }
        elif el.tag == "relation":
            rels[el.get("id")] = {
                "members": [(m.get("type"), m.get("ref"), m.get("role"))
                            for m in el.findall("member")],
                "tags": {t.get("k"): t.get("v") for t in el.findall("tag")},
            }
        if el.tag in ("node", "way", "relation"):
            el.clear()
    return nodes, ways, rels


def auto_bbox(nodes):
    lats = [p[0] for p in nodes.values()]
    lons = [p[1] for p in nodes.values()]
    return (min(lats), min(lons), max(lats), max(lons))


class Proj:
    """Projection locale équirectangulaire en mètres, puis en pixels."""

    def __init__(self, bbox, width):
        s, w, n, e = bbox
        self.lat0 = (s + n) / 2
        self.k = math.cos(math.radians(self.lat0))
        self.mx0 = self._mx(w)
        self.my0 = self._my(n)
        self.w_m = self._mx(e) - self.mx0
        self.h_m = self.my0 - self._my(s)
        self.width = width
        self.m_per_px = self.w_m / width
        self.height = int(round(self.h_m / self.m_per_px))

    def _mx(self, lon):
        return math.radians(lon) * 6371000 * self.k

    def _my(self, lat):
        return math.radians(lat) * 6371000

    def px(self, latlon):
        lat, lon = latlon
        x = (self._mx(lon) - self.mx0) / self.m_per_px
        y = (self.my0 - self._my(lat)) / self.m_per_px
        return (x, y)


def way_coords(way, nodes):
    return [nodes[n] for n in way["nodes"] if n in nodes]


def rel_outer_rings(rel, ways, nodes):
    """Assemble les membres 'outer' d'une relation en anneaux fermés."""
    segs = [way_coords(ways[r], nodes) for t, r, role in rel["members"]
            if t == "way" and r in ways and role in ("outer", "")]
    segs = [s for s in segs if len(s) >= 2]
    rings = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[-2::-1]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def load_font(size):
    """DejaVu Sans si disponible (accents), sinon la police bitmap de Pillow."""
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def polyline_midpoint(pts):
    """Point situé à mi-longueur d'une polyligne (en pixels)."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    half = sum(seg) / 2
    for (a, b), L in zip(zip(pts, pts[1:]), seg):
        if half <= L and L > 0:
            t = half / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        half -= L
    return pts[-1]


def draw_poly(d, proj, ring, fill, outline=None):
    pts = [proj.px(p) for p in ring]
    if len(pts) >= 3:
        d.polygon(pts, fill=fill, outline=outline)


def draw_line(d, proj, coords, width_m, fill):
    pts = [proj.px(p) for p in coords]
    w = max(1, int(round(width_m / proj.m_per_px)))
    if len(pts) >= 2:
        d.line(pts, fill=fill, width=w, joint="curve")
        r = w / 2
        for x, y in (pts[0], pts[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def render(osm_path, out_png, bbox=None, width=3000):
    nodes, ways, rels = parse_osm(osm_path)
    if not nodes:
        raise SystemExit(f"{osm_path} : aucun nœud")
    bbox = bbox or auto_bbox(nodes)
    proj = Proj(bbox, width)
    img = Image.new("RGB", (proj.width, proj.height), COL_BG)
    d = ImageDraw.Draw(img)

    def is_water(t):
        return t.get("natural") == "water" or t.get("waterway") in ("riverbank",) \
            or t.get("water") in ("river", "canal", "pond", "lake")

    def is_green(t):
        return t.get("leisure") in ("park", "garden") or t.get("landuse") in ("grass", "cemetery")

    stats = dict(eau=0, vert=0, batiments=0, rues=0, noms=0)

    # 1. surfaces : eau et verdure (relations puis ways), avant tout le reste
    for kind, col, test in (("eau", COL_WATER, is_water), ("vert", COL_GREEN, is_green)):
        for rel in rels.values():
            if test(rel["tags"]):
                for ring in rel_outer_rings(rel, ways, nodes):
                    draw_poly(d, proj, ring, col); stats[kind] += 1
        for way in ways.values():
            if test(way["tags"]) and way["nodes"] and way["nodes"][0] == way["nodes"][-1]:
                draw_poly(d, proj, way_coords(way, nodes), col); stats[kind] += 1
    # rivière tracée en ligne (si seule la ligne 'waterway=river' existe)
    for way in ways.values():
        if way["tags"].get("waterway") in ("river", "stream", "canal"):
            draw_line(d, proj, way_coords(way, nodes), 12 if way["tags"]["waterway"] == "river" else 3, COL_WATER)
            stats["eau"] += 1

    # 2. rues : bord puis cœur, pour un liseré léger
    streets = []
    for way in ways.values():
        hw = way["tags"].get("highway")
        if hw and hw not in SKIP_HIGHWAY and way["tags"].get("area") != "yes":
            streets.append((way, STREET_WIDTH.get(hw, 6)))
    for way, w in streets:
        draw_line(d, proj, way_coords(way, nodes), w + 2 * proj.m_per_px, COL_STREET_EDGE)
    for way, w in streets:
        draw_line(d, proj, way_coords(way, nodes), w, COL_STREET)
        stats["rues"] += 1

    # 3. bâtiments
    for rel in rels.values():
        if "building" in rel["tags"]:
            for ring in rel_outer_rings(rel, ways, nodes):
                draw_poly(d, proj, ring, COL_BUILDING); stats["batiments"] += 1
    for way in ways.values():
        if "building" in way["tags"] and len(way["nodes"]) >= 4:
            draw_poly(d, proj, way_coords(way, nodes), COL_BUILDING); stats["batiments"] += 1

    # 4. noms des rues, en petit, pour se repérer dans l'éditeur
    font = load_font(max(10, int(9 / proj.m_per_px)))
    seen = set()
    for way in ways.values():
        name = way["tags"].get("name")
        if not name or name in seen or "highway" not in way["tags"]:
            continue
        pts = [proj.px(c) for c in way_coords(way, nodes)]
        if len(pts) < 2:
            continue
        x, y = polyline_midpoint(pts)
        if 0 <= x < proj.width and 0 <= y < proj.height:
            d.text((x, y), name, fill=COL_NAME, font=font, anchor="mm")
            seen.add(name); stats["noms"] += 1

    img.save(out_png)
    meta = {
        "source": osm_path, "bbox": {"south": bbox[0], "west": bbox[1], "north": bbox[2], "east": bbox[3]},
        "width_px": proj.width, "height_px": proj.height,
        "m_per_px": round(proj.m_per_px, 4),
        "width_m": round(proj.w_m, 1), "height_m": round(proj.h_m, 1),
        "projection": "équirectangulaire locale, lat0=%.5f" % proj.lat0,
    }
    meta_path = out_png.rsplit(".", 1)[0] + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"écrit {out_png} ({proj.width}×{proj.height} px, {proj.m_per_px:.2f} m/px, "
          f"zone {proj.w_m:.0f}×{proj.h_m:.0f} m) et {meta_path}")
    print("éléments dessinés :", ", ".join(f"{k} {v}" for k, v in stats.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("osm", nargs="?", default="data/castres.osm")
    ap.add_argument("out", nargs="?", default="data/fond_castres.png")
    ap.add_argument("--bbox", help="sud,ouest,nord,est ; défaut : étendue du fichier")
    ap.add_argument("--width", type=int, default=3000, help="largeur du PNG en px")
    a = ap.parse_args()
    bbox = tuple(float(x) for x in a.bbox.split(",")) if a.bbox else None
    render(a.osm, a.out, bbox, a.width)


if __name__ == "__main__":
    main()
