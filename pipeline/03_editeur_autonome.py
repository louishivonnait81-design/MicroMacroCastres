"""
03_editeur_autonome.py — Fiche 006 : éditeur de plan en un seul fichier.

Embarque data/layout.json et le fond OSM aligné sur la grille dans une copie
de tools/layout-editor/index.html, pour que Louis n'ait qu'un fichier à
ouvrir dans son navigateur : rien à installer, rien à glisser-déposer.

Usage :
  python3 pipeline/03_editeur_autonome.py [layout.json] [fond.png] [sortie.html]
Par défaut : data/layout.json, data/fond_castres_grille.png,
             out/editeur_castres.html
"""

import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(HERE, "tools", "layout-editor", "index.html")


def build(layout_path, fond_path, out_path):
    html = open(TEMPLATE, encoding="utf-8").read()
    if "window.EMBED" not in html:
        raise SystemExit("index.html ne gère pas window.EMBED : mettre l'éditeur à jour")

    layout = json.load(open(layout_path, encoding="utf-8"))
    embed = {"layout": layout, "name": os.path.basename(layout_path)}
    if fond_path and os.path.exists(fond_path):
        data = open(fond_path, "rb").read()
        embed["bg"] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
        embed["bgName"] = os.path.basename(fond_path)

    # JSON sûr à l'intérieur d'une balise <script>
    blob = json.dumps(embed, ensure_ascii=False).replace("</", "<\\/")
    tag = "<script>window.EMBED = " + blob + ";</script>\n<script>"
    html = html.replace("<script>", tag, 1)
    html = html.replace("<title>", "<title>Castres — ", 1)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(html)
    ko = os.path.getsize(out_path) / 1024
    print("écrit %s (%.0f ko, plan %d × %d, %d monuments, %d labels%s)"
          % (out_path, ko, layout["cols"], layout["rows"],
             len(layout.get("monuments", [])), len(layout.get("labels", [])),
             ", fond embarqué" if "bg" in embed else ", sans fond"))


if __name__ == "__main__":
    a = sys.argv[1:]
    build(a[0] if len(a) > 0 else os.path.join(HERE, "data", "layout.json"),
          a[1] if len(a) > 1 else os.path.join(HERE, "data", "fond_castres_grille.png"),
          a[2] if len(a) > 2 else os.path.join(HERE, "out", "editeur_castres.html"))
