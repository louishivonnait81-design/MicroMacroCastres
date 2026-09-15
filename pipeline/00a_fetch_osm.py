#!/usr/bin/env python3
"""
00a_fetch_osm.py — Télécharge l'extrait OpenStreetMap du périmètre de
DECISIONS.md via l'API Overpass et l'enregistre dans data/castres.osm.

À lancer depuis une machine où le réseau autorise Overpass (le Mac de
Louis, par exemple) ; l'environnement Claude Code cloud refuse ces hôtes.

Usage :
  python3 pipeline/00a_fetch_osm.py                       # bbox par défaut
  python3 pipeline/00a_fetch_osm.py --bbox 43.600,2.232,43.612,2.250
  python3 pipeline/00a_fetch_osm.py --print-query         # affiche la requête,
                                                         # à coller sur overpass-turbo.eu

Sans dépendance hors bibliothèque standard.

Alternative manuelle : coller la requête (--print-query) sur
https://overpass-turbo.eu, lancer, puis Exporter → Données → « raw OSM
data » et enregistrer le fichier sous data/castres.osm.
"""

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Périmètre DECISIONS.md : rive gauche du bd Léon Bourgeois à l'Agout, du
# bd Miredames au bd Henri Sizaire ; rive droite le quartier Villegoudou
# jusqu'à la première rue parallèle à l'Agout. La bbox est prise avec une
# petite marge ; 00_osm_to_layout.py recadre ensuite sur les boulevards.
DEFAULT_BBOX = (43.598, 2.230, 43.614, 2.253)   # sud, ouest, nord, est

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def build_query(bbox):
    s, w, n, e = bbox
    bb = f"{s},{w},{n},{e}"
    # Tout ce dont les fiches 002 et suivantes ont besoin : rues, bâtiments,
    # eau, parcs, places, monuments nommés, arbres, ponts. Les relations
    # (multipolygones de bâtiments ou d'eau) sont incluses avec leurs membres.
    return f"""[out:xml][timeout:120][bbox:{bb}];
(
  way["highway"];
  way["building"];
  relation["building"];
  way["waterway"];
  relation["waterway"];
  way["natural"="water"];
  relation["natural"="water"];
  way["leisure"~"park|garden"];
  relation["leisure"~"park|garden"];
  way["landuse"~"grass|cemetery"];
  way["place"="square"];
  way["amenity"~"place_of_worship|townhall|theatre|marketplace"];
  relation["amenity"~"place_of_worship|townhall|theatre|marketplace"];
  way["historic"];
  relation["historic"];
  way["man_made"~"bridge|pier"];
  node["natural"="tree"];
  node["amenity"~"fountain|theatre|townhall|place_of_worship"];
);
(._;>;);
out meta;
"""


def fetch(query, mirrors):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for url in mirrors:
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"User-Agent": "micromacro-castres/0.1 (fetch_osm)"})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            if b"<osm" not in body[:2000]:
                raise RuntimeError("réponse sans balise <osm>")
            print(f"OK depuis {url} : {len(body)/1e6:.1f} Mo", file=sys.stderr)
            return body
        except (urllib.error.URLError, RuntimeError, OSError) as e:
            last = e
            print(f"échec {url} : {e}", file=sys.stderr)
    raise SystemExit(f"Aucun miroir Overpass n'a répondu ({last}). "
                     "Faire l'export à la main : voir --print-query.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", help="sud,ouest,nord,est (degrés)")
    ap.add_argument("--out", default="data/castres.osm")
    ap.add_argument("--print-query", action="store_true")
    a = ap.parse_args()
    bbox = tuple(float(x) for x in a.bbox.split(",")) if a.bbox else DEFAULT_BBOX
    if len(bbox) != 4:
        raise SystemExit("--bbox attend 4 nombres")
    q = build_query(bbox)
    if a.print_query:
        print(q)
        return
    body = fetch(q, MIRRORS)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(body)
    print(f"écrit {a.out}")


if __name__ == "__main__":
    main()
