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
  "legend": {"r":"rue","b":"boulevard","I":"ilot","p":"place","P":"parc","w":"eau","q":"quai",".":"vide"},
  "monuments": [{"id":"saint-benoit","x":40,"y":12,"w":10,"h":16,"levels":6}],
  "labels": [{"text":"Place Jean-Jaurès","x":50,"y":30}] }
```
`cells` : une lettre par case, `rows` lignes de `cols` caractères, séparées par `\n`.

## Partie A — `pipeline/00_osm_to_layout.py`
1. Projeter les rues OSM (highway hors autoroutes) en mètres, appliquer le facteur de compression de `DECISIONS.md` (0,097 case/m, calculé pour que le périmètre tienne dans la grille, marge à l'est ; afficher le facteur). Le tracé et les positions relatives sont conservés ; seules les longueurs sont compressées. Ne garder que les boulevards, les rues principales et les cinq rues nommées.
2. Redresser chaque rue sur les axes 0°/90° de la grille (polyligne simplifiée, chaque segment accroché à l'axe le plus proche), largeur minimale 4 cases, boulevards 6.
3. Tout ce qui est entouré de voies devient `I` (îlot plein). Le périmètre et le facteur sont fixés par `DECISIONS.md` ; on ne les rediscute pas ici.
   **Règles du 16/09 (Louis), qui remplacent celles du 15/09** :
   - *Réseau* : l'intégralité du réseau piéton et routier réel du périmètre est gardée (rues, ruelles, venelles, passages, escaliers, allées de la place et du jardin). Aucune voie supprimée ; chaque voie garde ses connexions réelles (le script ajoute un raccord d'une case là où le redressement les aurait rompues). Un Castrais doit pouvoir suivre n'importe quel trajet de la vraie ville sur la carte.
   - *Largeur selon le caractère* : venelle 1 case, ruelle 2, rue 3, rues nommées de DECISIONS 4, boulevards et quais 6 à 8 avec arbres (lettre `b` dans la grille). Pas d'escalier de cases : au plus un coude à angle droit toutes les 8 cases.
   - *Îlots* : les bâtiments n'ont aucune fidélité à respecter, sauf les monuments à leur position (décalages explicites dans le script ; les voies qu'ils recouvrent sont comptées). Tout ce qui n'est pas voie, place, parc ou eau devient îlot, rempli à 100 %, un à deux immeubles par îlot, sans case vide. Plus de découpe ni de ceinture autour de la place.
   - *Vide* : le pourcentage n'est plus qu'une information.
   - *Règles du 17/09* : largeurs venelle 1, rue ordinaire et ruelle 2, avenue et voie primaire 3, cinq rues nommées 4, boulevards Léon Bourgeois / Miredames / Henri Sizaire et quais 5. Un îlot de moins de 4 cases de côté devient une maison unique à 2 niveaux (lettre `m`), jamais une raison de supprimer une voie. Les voies gagnent sur tout, monuments compris : l'emprise de chaque monument est rognée au plus grand rectangle libre de toute voie, d'eau, de place et d'autre monument ; sous la moitié de l'emprise prévue, le script le signale au lieu de déplacer le monument.
   - *Tri du réseau (16/09, soir)* : sont écartés d'office les footway `sidewalk` / `crossing`, les `service` sans nom, les `path`, `cycleway`, les `steps` sans nom, et toute voie sans nom OSM qui longe une autre voie à moins de 2 cases sur plus de la moitié de sa longueur (doublon de trottoir). Largeur 6 réservée aux boulevards Léon Bourgeois, Miredames, Henri Sizaire et aux quais ; avenues et voies primaires à 4. La liste des voies supprimées avec leur raison est écrite dans `out/voies_supprimees.txt`.
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
