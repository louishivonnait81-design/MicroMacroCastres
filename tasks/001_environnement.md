# 001 — Environnement et preuve du pipeline de rendu

## Objectif
Faire tourner Blender comme module Python dans cet environnement et produire un rendu ligne claire PNG **et** SVG à partir d'un fichier de test, sans aucune intervention manuelle.

## Entrées
- `pipeline/02_build_blender.py` (écrit pour Blender 3.6 ; a déjà tourné sous bpy 5.0 sans modification, sauf l'export SVG)
- `pipeline/legacy_generalize_osm.py` : produit un GeoJSON de test à partir d'un `.osm` (sert uniquement à fabriquer un jeu de données de test ici ; ne fait pas partie du pipeline v2)
- `data/test_rendu_cloud.png` : le résultat attendu, obtenu le 15/09/2026

## Étapes
1. Installer Python 3.11 (`uv python install 3.11` ou équivalent), créer un venv, `pip install bpy shapely numpy`. Vérifier `import bpy; bpy.app.version_string`.
2. Fabriquer une ville synthétique de test (quelques bâtiments, 3 rues, un parc, un plan d'eau) → `data/test.geojson`, via `legacy_generalize_osm.py` sur un petit `.osm` généré par script.
3. Lancer `python pipeline/02_build_blender.py -- data/test.geojson out/ 1600`. Le PNG doit ressembler à `data/test_rendu_cloud.png`.
4. Obtenir un SVG. Essayer dans l'ordre, s'arrêter au premier qui marche :
   a. installer l'extension « Freestyle SVG Exporter » depuis extensions.blender.org (si le réseau le permet) et activer `scene.svg_export`;
   b. Grease Pencil Line Art : créer un objet GP avec modificateur Line Art sur la scène, `bake`, puis `bpy.ops.wm.grease_pencil_export_svg` (nom exact à vérifier dans l'API 5.0) ;
   c. vectoriser le PNG avec potrace (`apt`/`pip` selon disponibilité) en gardant une résolution élevée (8000 px de large).
   Documenter le choix retenu dans `pipeline/README.md`, avec sa limite (par exemple : potrace produit des contours fermés, pas des traits).
5. Écrire `Makefile` ou `run.sh` : `make test-render` reproduit tout depuis zéro.

## Critère de réussite
`make test-render` produit `out/castres.png` et `out/castres.svg` ; le SVG ouvert dans un navigateur montre les mêmes lignes que le PNG ; aucune ligne cachée n'apparaît (les faces arrière des boîtes ne se voient pas).

## Hors périmètre
La vraie carte de Castres, l'éditeur de grille, tout ce qui touche à Gemini.
