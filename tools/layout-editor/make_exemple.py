#!/usr/bin/env python3
"""
make_exemple.py — Fabrique un layout.json synthétique 106 × 71 pour tester
l'éditeur sans attendre le brouillon réel (fiche 002 partie A) :
un damier de rues et d'îlots, une place, un jardin, une rivière avec ses
quais, deux ponts, six monuments et deux labels. Contient volontairement
une rue de 2 cases pour tester l'alerte.

Usage : python3 tools/layout-editor/make_exemple.py [sortie.json]
"""

import json
import sys

COLS, ROWS = 106, 71


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tools/layout-editor/exemple_layout.json"
    g = [["I"] * COLS for _ in range(ROWS)]

    def rect(ch, x, y, w, h):
        for j in range(max(0, y), min(ROWS, y + h)):
            for i in range(max(0, x), min(COLS, x + w)):
                g[j][i] = ch

    # rues horizontales (4 cases) et un boulevard (6, lettre b) en bas
    for y in (0, 14, 28, 44, 58):
        rect("r", 0, y, COLS, 4)
    rect("b", 0, 65, COLS, 6)
    # rues verticales
    for x in (0, 16, 34, 52, 100):
        rect("r", x, 0, 4, ROWS)
    # une rue trop étroite (2 cases) pour l'alerte
    rect("r", 26, 4, 2, 10)
    # place Jean-Jaurès et jardin
    rect("p", 38, 18, 20, 12)
    rect("P", 20, 32, 14, 10)
    # l'Agout : rivière oblique en marches, quais de 2 cases
    for y in range(ROWS):
        x0 = 76 + (y // 12)
        rect("q", x0 - 2, y, 2, 1)
        rect("w", x0, y, 10, 1)
        rect("q", x0 + 10, y, 2, 1)
    # deux ponts (les rues traversent l'eau)
    rect("r", 74, 28, 16, 4)
    rect("r", 76, 58, 16, 4)
    # rive droite : rue parallèle
    rect("r", 92, 0, 4, ROWS)

    cells = "\n".join("".join(row) for row in g)
    layout = {
        "cols": COLS, "rows": ROWS, "cell_cm": 1.0,
        "cells": cells,
        "legend": {"r": "rue", "b": "boulevard", "I": "ilot", "m": "maison", "p": "place", "P": "parc",
                   "w": "eau", "q": "quai", ".": "vide"},
        "monuments": [
            {"id": "saint-benoit", "x": 56, "y": 32, "w": 10, "h": 14, "levels": 3},
            {"id": "eveche-mairie", "x": 20, "y": 18, "w": 12, "h": 7, "levels": 3},
            {"id": "jardin-eveche", "x": 20, "y": 32, "w": 14, "h": 10, "levels": 0},
            {"id": "theatre", "x": 38, "y": 32, "w": 7, "h": 6, "levels": 3},
            {"id": "maisons-agout", "x": 56, "y": 48, "w": 20, "h": 4, "levels": 3},
            {"id": "pont-vieux", "x": 76, "y": 28, "w": 12, "h": 4, "levels": 0},
        ],
        "labels": [
            {"text": "Place Jean-Jaurès", "x": 48, "y": 24},
            {"text": "Agout", "x": 82, "y": 10},
        ],
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    print("écrit", out)


if __name__ == "__main__":
    main()
