# 002 — Éditeur de grille et brouillon automatique du plan de jeu

## Objectif
Un fichier `tools/layout-editor/index.html` (sans serveur, sans dépendance réseau) pour corriger case par case un `layout.json`, et un script qui génère un premier brouillon à partir d'OSM pour que Louis ne parte pas d'une grille vide.

## Entrées
- `DECISIONS.md` (dimensions de la grille, échelles, périmètre, monuments)
- `data/castres.osm` (export OpenStreetMap de la zone : `python3 pipeline/00a_fetch_osm.py` sur le Mac, ou export manuel depuis overpass-turbo.eu avec la requête de `--print-query` ; le réseau de Claude Code cloud refuse Overpass)
- `data/fond_castres.png` + `data/fond_castres.json` (fond de l'éditeur généré par `python3 pipeline/00b_osm_to_fond.py` : rues, bâtiments, rivière en gris clair, avec son géoréférencement ; remplace la capture d'écran)

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
1. Projeter les rues OSM (highway hors autoroutes) en mètres, appliquer le facteur de compression de `DECISIONS.md` (0,097 case/m, calculé pour que le périmètre tienne dans la grille, marge à l'est ; afficher le facteur). Le tracé et les positions relatives sont conservés ; seules les longueurs sont compressées. Ne garder que les boulevards, les rues principales et les cinq rues nommées.
2. Redresser chaque rue sur les axes 0°/90° de la grille (polyligne simplifiée, chaque segment accroché à l'axe le plus proche), largeur minimale 4 cases, boulevards 6.
3. Tout ce qui est entouré de rues devient `I`. Le facteur de compression fixe uniquement les positions ; la part de vide se gagne ensuite sur les îlots, jamais en réduisant le périmètre :
   a. élargir les rues à 4 cases (6 pour les boulevards) en érodant les îlots ;
   b. couper tout îlot de plus de 12 cases de côté par une rue intérieure de 3 cases ;
   c. répéter a–b jusqu'à ce que rues + places + parcs représentent au moins 33 % de la grille.
   Le périmètre et le facteur sont fixés par `DECISIONS.md` ; on ne les rediscute pas ici.
   **Règles ajoutées le 15/09 (Louis)** :
   - *Rues* : aucune rue en escalier. Chaque rue redressée est au plus deux segments droits avec un coude à angle droit (droite ou L, Victor Hugo devient un L). Les tronçons OSM d'une même rue sont fusionnés d'abord. Un boulevard qui ne tient pas en deux segments à 6 cases près est supprimé et signalé ; les cinq rues nommées sont toujours gardées.
   - *Réseau* : on ne garde que les boulevards (6 cases), les cinq rues nommées (4 cases), les ponts, et les découpes strictement nécessaires pour qu'aucun îlot ne dépasse 12 cases (rues intérieures de 3 cases, nombre minimal, réparties régulièrement). Tout le reste, y compris les rues « principales » d'OSM, est supprimé. Objectif de vide hors eau : 35–40 %. Au-dessus de 40 %, on retire les coupes dont la suppression ne crée pas d'îlot > 12.
   - *Place* : la place Jean-Jaurès fait 18 × 8, à 6 cases de la rive. Elle est bordée d'îlots accolés sur ses quatre côtés, façades sur la place, le théâtre (7 × 6) étant l'îlot sud à son extrémité ouest. Les rues n'y débouchent que par quatre trouées de 4 cases aux angles, en moulinet (NW → nord, NE → est, SE → sud, SW → ouest), prolongées jusqu'à la première rue ; aucune rue ne longe la place.
4. Poser `p` (place Jean-Jaurès), `P` (jardin), `w` (Agout, largeur 8–12 cases), `q` (quais, 2 cases le long de l'eau) d'après les polygones OSM, redressés.
5. Réserver les rectangles des monuments de `DECISIONS.md` (position d'après OSM `name`).
6. Écrire `data/layout.json` + un PNG de contrôle en couleurs `out/layout_preview.png` (une couleur par type, monuments hachurés, grille A–G / 1–4 en marge, facteur de compression et pourcentage rues + places + parcs affichés dans la marge).

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
