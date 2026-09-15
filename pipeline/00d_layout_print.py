#!/usr/bin/env python3
"""
00d_layout_print.py — Fiche 003 : impression de contrôle du plan de jeu.

Produit out/layout_A3.png (A3 portrait ou paysage selon la grille, 300 dpi) et
out/layout_A3.pdf à partir de data/layout.json : une couleur par type de
case, monuments hachurés avec leur id, marges A–G / 1–4 comme sur le papier,
légende et échelle. La grille entière tient sur la feuille (1 case ≈ 3,7 mm),
pour être posée à côté de la carte MicroMacro et comparée à l'œil.

Usage :
  python3 pipeline/00d_layout_print.py                      # data/layout.json → out/layout_A3.*
  python3 pipeline/00d_layout_print.py data/layout.json out/layout_A3.png

Dépendance : pillow.
"""

import importlib.util
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fond", os.path.join(HERE, "00b_osm_to_fond.py"))
fond = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fond)

DPI = 300
A3_MM = (420, 297)
COLORS = {"r": (227, 227, 227), "b": (205, 214, 196), "I": (201, 162, 126), "m": (166, 118, 80), "p": (243, 214, 107),
          "P": (159, 211, 155), "w": (142, 193, 230), "q": (220, 205, 176), ".": (255, 255, 255)}
EXTRA = [(230, 160, 196), (160, 196, 230), (196, 230, 160)]


def mm(v):
    return int(round(v / 25.4 * DPI))


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data/layout.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "out/layout_A3.png"
    with open(src, encoding="utf-8") as f:
        lay = json.load(f)
    cols, rows = lay["cols"], lay["rows"]
    legend = lay.get("legend", {})
    colors = dict(COLORS)
    for i, k in enumerate(k for k in legend if k not in colors):
        colors[k] = EXTRA[i % len(EXTRA)]
    portrait = cols < rows
    W, H = (mm(A3_MM[1]), mm(A3_MM[0])) if portrait else (mm(A3_MM[0]), mm(A3_MM[1]))
    bx, by = ("1234", "ABCDEFG") if portrait else ("ABCDEFG", "1234")
    margin, header = mm(18), mm(14)
    cell = min((W - 2 * margin) // cols, (H - 2 * margin - header) // rows)
    ox = (W - cols * cell) // 2
    oy = header + (H - header - rows * cell) // 2
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    grid = lay["cells"].split("\n")
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            d.rectangle([ox + x * cell, oy + y * cell, ox + (x + 1) * cell - 1, oy + (y + 1) * cell - 1], fill=colors.get(c, (255, 0, 255)))
    # trait fin par case, trait fort par bande
    for x in range(cols + 1):
        d.line([ox + x * cell, oy, ox + x * cell, oy + rows * cell], fill=(120, 120, 120), width=1)
    for y in range(rows + 1):
        d.line([ox, oy + y * cell, ox + cols * cell, oy + y * cell], fill=(120, 120, 120), width=1)
    for i in range(len(bx) + 1):
        x = ox + round(i * cols / len(bx)) * cell
        d.line([x, oy - mm(2), x, oy + rows * cell + mm(2)], fill=(0, 0, 0), width=mm(0.4))
    for j in range(len(by) + 1):
        y = oy + round(j * rows / len(by)) * cell
        d.line([ox - mm(2), y, ox + cols * cell + mm(2), y], fill=(0, 0, 0), width=mm(0.4))
    big = fond.load_font(mm(6)); small = fond.load_font(mm(2.6)); tiny = fond.load_font(mm(2.0))
    for i, L in enumerate(bx):
        d.text((ox + (i + .5) * cols / len(bx) * cell, oy - mm(6)), L, fill=(0, 0, 0), font=big, anchor="mm")
    for j, L in enumerate(by):
        d.text((ox - mm(8), oy + (j + .5) * rows / len(by) * cell), L, fill=(0, 0, 0), font=big, anchor="mm")
    used_labels = []
    for m in lay.get("monuments", []):
        x0, y0 = ox + m["x"] * cell, oy + m["y"] * cell
        x1, y1 = x0 + m["w"] * cell, y0 + m["h"] * cell
        step = max(cell, mm(1.5))
        for k in range(-m["h"] * cell, m["w"] * cell, step):
            xa, xb, ya, yb = x0 + k, x0 + k + m["h"] * cell, y0, y1
            if xa < x0:
                ya = y0 + (x0 - xa); xa = x0
            if xb > x1:
                yb = y1 - (xb - x1); xb = x1
            if xb > xa:
                d.line([xa, ya, xb, yb], fill=(0, 0, 0), width=1)
        d.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=mm(0.3))
        lx_, ly_ = x0 + 3, y0 + 2
        if any(abs(lx_ - ux) < mm(15) and abs(ly_ - uy) < mm(4) for ux, uy in used_labels):
            lx_, ly_ = x0 + 3, y1 - mm(3.5)
        tw_ = d.textlength(m["id"], font=tiny)
        d.rectangle([lx_ - 1, ly_, lx_ + tw_ + 1, ly_ + mm(2.6)], fill=(255, 255, 255))
        d.text((lx_, ly_), m["id"], fill=(0, 0, 0), font=tiny)
        used_labels.append((lx_, ly_))
    for l in lay.get("labels", []):
        x, y = ox + (l["x"] + .5) * cell, oy + (l["y"] + .5) * cell
        tw = d.textlength(l["text"], font=small)
        d.rectangle([x - 2, y - mm(1.5), x + tw + 2, y + mm(1.5)], fill=(255, 255, 255))
        d.text((x, y), l["text"], fill=(31, 95, 191), font=small, anchor="lm")
    meta = lay.get("meta", {})
    d.text((ox, mm(4)), f"MicroMacro-Castres — plan de jeu — grille {cols} × {rows} cases, 1 case = 1 cm sur la carte finale "
           f"(ici {cell / DPI * 25.4:.1f} mm) — vide {meta.get('open_share_land', '?')} % hors eau — "
           f"imprimer à 100 % sur A3 {'portrait' if portrait else 'paysage'}", fill=(0, 0, 0), font=small)
    lx = ox
    for k, name in legend.items():
        d.rectangle([lx, mm(8.5), lx + mm(3), mm(11.5)], fill=colors[k], outline=(0, 0, 0))
        d.text((lx + mm(3.6), mm(10)), f"{k} {name}", fill=(0, 0, 0), font=tiny, anchor="lm")
        lx += mm(20)
    d.text((lx + mm(4), mm(10)), "monuments hachurés", fill=(0, 0, 0), font=tiny, anchor="lm")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, dpi=(DPI, DPI))
    pdf = out.rsplit(".", 1)[0] + ".pdf"
    img.save(pdf, "PDF", resolution=DPI)
    print(f"écrit {out} ({W} × {H} px, {cell / DPI * 25.4:.2f} mm par case) et {pdf}")


if __name__ == "__main__":
    main()
