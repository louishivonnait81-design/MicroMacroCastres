#!/usr/bin/env python3
"""
check_layout.py — Valide un layout.json (format de la fiche 002) et affiche
ses statistiques : cases par type, part rues + places + parcs (objectif
≥ 33 %), rues de moins de 3 cases, monuments hors grille.

Usage :
  python3 pipeline/check_layout.py data/layout.json
  python3 pipeline/check_layout.py data/layout.json --json     # stats en JSON

Code de retour 0 si le fichier est valide, 1 sinon. C'est ce script que
les fiches suivantes (004…) utilisent pour accepter un layout.
Bibliothèque standard seulement.
"""

import argparse
import json
import sys

DEFAULT_LEGEND = {"r": "rue", "I": "ilot", "p": "place", "P": "parc",
                  "w": "eau", "q": "quai", ".": "vide"}
OPEN_TYPES = "rpP"        # rues + places + parcs : la part de « vide »
STREET = "r"
MIN_STREET = 3


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(lay):
    """Renvoie (liste d'erreurs, lignes de la grille)."""
    err = []
    for k in ("cols", "rows", "cells"):
        if k not in lay:
            err.append(f"clé manquante : {k}")
    if err:
        return err, []
    cols, rows = lay["cols"], lay["rows"]
    if not (isinstance(cols, int) and isinstance(rows, int) and cols > 0 and rows > 0):
        err.append("cols et rows doivent être des entiers positifs")
        return err, []
    legend = lay.get("legend") or DEFAULT_LEGEND
    lines = lay["cells"].split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) != rows:
        err.append(f"cells : {len(lines)} lignes, rows = {rows}")
    for i, ln in enumerate(lines):
        if len(ln) != cols:
            err.append(f"cells ligne {i} : {len(ln)} caractères, cols = {cols}")
            break
    bad = sorted({c for ln in lines for c in ln if c not in legend})
    if bad:
        err.append(f"caractères hors légende : {bad}")
    for m in lay.get("monuments", []):
        for k in ("id", "x", "y", "w", "h"):
            if k not in m:
                err.append(f"monument sans {k} : {m}")
                break
        else:
            if m["x"] < 0 or m["y"] < 0 or m["x"] + m["w"] > cols or m["y"] + m["h"] > rows:
                err.append(f"monument {m['id']} hors grille")
            if m["w"] <= 0 or m["h"] <= 0:
                err.append(f"monument {m['id']} d'emprise nulle")
    ids = [m.get("id") for m in lay.get("monuments", [])]
    if len(ids) != len(set(ids)):
        err.append("identifiants de monuments en double")
    for lb in lay.get("labels", []):
        if "text" not in lb or "x" not in lb or "y" not in lb:
            err.append(f"label incomplet : {lb}")
    return err, lines


def narrow_streets(lines, cols, rows):
    """Cases de rue dont l'épaisseur (min des séries horizontale et verticale)
    est < 3. Renvoie la liste des (x, y)."""
    hrun = [[0] * cols for _ in range(rows)]
    vrun = [[0] * cols for _ in range(rows)]
    for y in range(rows):
        x = 0
        while x < cols:
            if lines[y][x] == STREET:
                x0 = x
                while x < cols and lines[y][x] == STREET:
                    x += 1
                for i in range(x0, x):
                    hrun[y][i] = x - x0
            else:
                x += 1
    for x in range(cols):
        y = 0
        while y < rows:
            if lines[y][x] == STREET:
                y0 = y
                while y < rows and lines[y][x] == STREET:
                    y += 1
                for j in range(y0, y):
                    vrun[j][x] = y - y0
            else:
                y += 1
    return [(x, y) for y in range(rows) for x in range(cols)
            if lines[y][x] == STREET and min(hrun[y][x], vrun[y][x]) < MIN_STREET]


def stats(lay, lines):
    cols, rows = lay["cols"], lay["rows"]
    legend = lay.get("legend") or DEFAULT_LEGEND
    total = cols * rows
    counts = {k: 0 for k in legend}
    for ln in lines:
        for c in ln:
            counts[c] = counts.get(c, 0) + 1
    open_cells = sum(counts.get(c, 0) for c in OPEN_TYPES)
    narrow = narrow_streets(lines, cols, rows)
    return {
        "cols": cols, "rows": rows, "total": total,
        "counts": {f"{k} ({legend[k]})": v for k, v in counts.items()},
        "open_share": round(100 * open_cells / total, 1),
        "open_target": 33.0,
        "narrow_street_cells": len(narrow),
        "monuments": len(lay.get("monuments", [])),
        "labels": len(lay.get("labels", [])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    lay = load(a.path)
    err, lines = validate(lay)
    if err:
        for e in err:
            print("ERREUR :", e)
        sys.exit(1)
    st = stats(lay, lines)
    if a.json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
    else:
        print(f"{a.path} : valide, {st['cols']}×{st['rows']} = {st['total']} cases")
        for k, v in st["counts"].items():
            print(f"  {k:12s} {v:6d}  {100*v/st['total']:5.1f} %")
        ok = "OK" if st["open_share"] >= st["open_target"] else "sous l'objectif"
        print(f"  rues + places + parcs : {st['open_share']} % (objectif ≥ 33 %) → {ok}")
        print(f"  cases de rue < 3 de large : {st['narrow_street_cells']}")
        print(f"  monuments : {st['monuments']}, labels : {st['labels']}")


if __name__ == "__main__":
    main()
