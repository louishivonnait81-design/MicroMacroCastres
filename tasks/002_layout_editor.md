# 002 — Éditeur de grille et brouillon automatique du plan de jeu

## Objectif
Un fichier `tools/layout-editor/index.html` (sans serveur, sans dépendance réseau) pour corriger case par case un `layout.json`, et un script qui génère un premier brouillon à partir d'OSM pour que Louis ne parte pas d'une grille vide.

## Entrées
- `DECISIONS.md` (dimensions de la grille, échelles, périmètre, monuments)
- `data/castres.osm` (export OpenStreetMap de la zone, fourni par Louis)
- `data/fond_castres.png` (capture d'écran de la carte de la zone, fournie par Louis)

## Format `layout.json`
```json
{ "cols": 106, "rows": 71, "cell_cm": 1.0,
  "cells": "…",  
  "legend": {"r":"rue","I":"ilot","p":"place","P":"parc","w":"eau","q":"quai",".":"vide"},
  "monuments": [{"id":"saint-benoit","x":40,"y":12,"w":10,"h":16,"levels":6}],
  "labels": [{"text":"Place Jean-Jaurès","x":50,"y":30}] }
```
`cells` : une lettre par case, `rows` lignes de `cols` caractères, séparées par `\n`.

## Partie A — `pipeline/00_osm_to_layout.py`
1. Projeter les rues OSM (highway hors autoroutes) en mètres, choisir un facteur de compression mètres → cases tel que le périmètre de `DECISIONS.md` tienne dans la grille (afficher le facteur ; attendu 0,6–0,75). Le tracé et les positions relatives sont conservés ; seules les longueurs sont compressées.
2. Redresser chaque rue sur les axes 0°/90° de la grille (polyligne simplifiée, chaque segment accroché à l'axe le plus proche), largeur minimale 4 cases, boulevards 6.
3. Tout ce qui est entouré de rues devient `I` ; les grands îlots (> 12 cases de côté) sont coupés en deux par une rue de 3 cases.
4. Poser `p` (place Jean-Jaurès), `P` (jardin), `w` (Agout, largeur 8–12 cases), `q` (quais, 2 cases le long de l'eau) d'après les polygones OSM, redressés.
5. Réserver les rectangles des monuments de `DECISIONS.md` (position d'après OSM `name`).
6. Écrire `data/layout.json` + un PNG de contrôle en couleurs `out/layout_preview.png` (une couleur par type, monuments hachurés, grille A–G / 1–4 en marge).

## Partie B — `tools/layout-editor/index.html`
- Charge un `layout.json` (bouton ou glisser-déposer) et une image de fond optionnelle avec opacité réglable.
- Grille zoomable, une lettre = une couleur (légende visible), pinceaux : clic, glisser, ligne droite (shift), rectangle, seau.
- Outil monument : tracer un rectangle, saisir id et niveaux.
- Panneau : compteur de cases par type, part de rue+place+parc (objectif ≥ 33 %), alerte si une rue < 3 cases.
- Export `layout.json` (téléchargement) — Louis le dépose dans `data/`.
- Doit rester fluide sur un MacBook Air 2017 dans Safari/Chrome : canvas, pas de DOM par case.

## Critère de réussite
`python pipeline/00_osm_to_layout.py` produit un `layout.json` et son PNG de contrôle ; l'éditeur l'ouvre, permet de modifier 20 cases et de réexporter un JSON valide que le script de la fiche 004 acceptera. Le PNG de contrôle imprimé en A3 doit se comparer à l'œil avec la carte MicroMacro (rues larges, îlots petits).

## Hors périmètre
Les volumes 3D, les fenêtres, tout rendu Blender (fiche 004–005).
