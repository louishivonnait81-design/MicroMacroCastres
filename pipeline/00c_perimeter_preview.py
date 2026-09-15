#!/usr/bin/env python3
"""
00c_perimeter_preview.py — PNG de contrôle d'un périmètre : le fond gris
(rues, bâtiments, rivière) avec, par-dessus, la grille 106 × 71 cases à
l'échelle du facteur de compression maximal qui fait tenir ce périmètre.
Sert à comparer deux périmètres avant de choisir (fiche 002, partie A).

Usage :
  python3 pipeline/00c_perimeter_preview.py --bbox 43.6010,2.2335,43.6076,2.2450 \
      --title "A — périmètre DECISIONS" --out out/perimetre_A.png
  options : --factor 0.10 (cases par mètre ; défaut : le maximum qui tient)
            --cols 106 --rows 71 --width 2400

Dépendance : pillow ; réutilise pipeline/00b_osm_to_fond.py.
"""

import argparse
import importlib.util
import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fond", os.path.join(HERE, "00b_osm_to_fond.py"))
fond = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/castres.osm")
    ap.add_argument("--bbox", required=True, help="sud,ouest,nord,est")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--factor", type=float, help="cases par mètre (défaut : maximum qui tient)")
    ap.add_argument("--cols", type=int, default=106)
    ap.add_argument("--rows", type=int, default=71)
    ap.add_argument("--width", type=int, default=2400)
    ap.add_argument("--margin", type=float, default=0.12, help="marge autour du périmètre (fraction)")
    a = ap.parse_args()

    s, w, n, e = (float(x) for x in a.bbox.split(","))
    lat0 = (s + n) / 2
    W_m = (e - w) * 111320 * math.cos(math.radians(lat0))
    H_m = (n - s) * 111320
    f = a.factor or min(a.cols / W_m, a.rows / H_m)
    grid_w_m, grid_h_m = a.cols / f, a.rows / f

    # fond rendu avec une marge autour du périmètre
    dlat, dlon = (n - s) * a.margin, (e - w) * a.margin
    big = (s - dlat, w - dlon, n + dlat, e + dlon)
    tmp = a.out + ".fond.png"
    fond.render(a.osm, tmp, big, a.width)
    img = Image.open(tmp).convert("RGB")
    os.remove(tmp); os.remove(tmp.rsplit(".", 1)[0] + ".json")
    proj = fond.Proj(big, a.width)
    d = ImageDraw.Draw(img, "RGBA")

    # périmètre demandé (rouge) et grille (bleu) centrée sur le périmètre
    x0, y0 = proj.px((n, w)); x1, y1 = proj.px((s, e))
    d.rectangle([x0, y0, x1, y1], outline=(200, 30, 30, 255), width=4)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cell = (1 / f) / proj.m_per_px            # px par case
    gx0, gy0 = cx - a.cols * cell / 2, cy - a.rows * cell / 2
    gx1, gy1 = gx0 + a.cols * cell, gy0 + a.rows * cell
    for i in range(a.cols + 1):
        x = gx0 + i * cell
        band = i % round(a.cols / 7) == 0 or i == a.cols
        d.line([x, gy0, x, gy1], fill=(30, 90, 200, 230 if band else 70), width=3 if band else 1)
    for j in range(a.rows + 1):
        y = gy0 + j * cell
        band = j % round(a.rows / 4) == 0 or j == a.rows
        d.line([gx0, y, gx1, y], fill=(30, 90, 200, 230 if band else 70), width=3 if band else 1)
    font = fond.load_font(max(18, int(cell * 1.2)))
    for i, L in enumerate("ABCDEFG"):
        d.text((gx0 + (i + .5) * a.cols / 7 * cell, gy0 - 1.2 * cell), L, fill=(30, 90, 200), font=font, anchor="mm")
    for j, L in enumerate("1234"):
        d.text((gx0 - 1.2 * cell, gy0 + (j + .5) * a.rows / 4 * cell), L, fill=(30, 90, 200), font=font, anchor="mm")

    # échelle : ce que font 1 case, une rue de 4 cases, un personnage
    big_font = fond.load_font(34)
    small_font = fond.load_font(26)
    lines = [
        a.title,
        f"périmètre (rouge) : {W_m:.0f} × {H_m:.0f} m — grille {a.cols} × {a.rows} cases (bleu) = {grid_w_m:.0f} × {grid_h_m:.0f} m",
        f"facteur de compression : {f:.3f} case/m — 1 case = {1/f:.1f} m — une rue de 4 cases = {4/f:.0f} m réels",
    ]
    pad = 14
    tw = max(d.textlength(t, font=big_font if k == 0 else small_font) for k, t in enumerate(lines))
    d.rectangle([pad, pad, pad + tw + 2 * pad, pad + 34 + 2 * 30 + 2 * pad], fill=(255, 255, 255, 235), outline=(0, 0, 0))
    y = 2 * pad
    for k, t in enumerate(lines):
        d.text((2 * pad, y), t, fill=(0, 0, 0), font=big_font if k == 0 else small_font)
        y += 40 if k == 0 else 30
    img.save(a.out)
    print(f"écrit {a.out} : périmètre {W_m:.0f}×{H_m:.0f} m, facteur {f:.3f} (1 case = {1/f:.1f} m)")


if __name__ == "__main__":
    main()
