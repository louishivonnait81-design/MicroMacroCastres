# MicroMacro-Castres — squelette du projet (v2, reprise de zéro)

## Pourquoi une v2

La v1 partait du cadastre OSM importé par Blosm. Résultat : une boîte par parcelle, toits automatiques illisibles, ruelles sans largeur. MicroMacro n'est pas un plan réel : ses rues suivent les deux axes de l'isométrie, ses immeubles sont des boîtes à 2–4 niveaux, ses rues sont énormes. La v2 **compose** une carte inspirée de Castres sur une grille, au lieu de l'**extraire** de Castres.

## Limites établies (à ne plus rediscuter)

| Limite | Conséquence dans le process |
|---|---|
| Louis ne dessine pas | Aucune étape ne demande de tracer. On peint des cases, on choisit, on place. |
| L'IA d'images est fiable sur un élément isolé, jamais sur une carte entière | L'IA ne voit jamais la carte. Elle produit des monuments, des détails, des personnages, un par un. |
| Pas de contrôle qualité automatique des images (leçon NYC) | Règle « quatre essais, on garde un, on ne retouche jamais ». |
| Style MicroMacro = iso stricte 30°, trait fin uniforme, aucune ombre, façades bêtes | Freestyle en ligne claire suffit ; pas de kit de façades IA ; fenêtres procédurales. |
| Bâtiments bas, rues larges, toits = scènes, rien de caché | Réglé à la main dans le plan de jeu (phase 1), pas par un algorithme. |
| Échelle jouet (personnage ≈ voiture/2 ≈ immeuble/6) | 1 case = 1 cm papier = 1 personnage. Tout le reste en découle. |
| MacBook Air 2017, pas de GPU | Tout tourne dans l'environnement Claude Code (cloud) : Blender comme module Python (`pip install bpy`, Python 3.11), Cycles CPU 1 échantillon — rendu de test prouvé en 3 s (`data/test_rendu_cloud.png`). Le Mac ne sert qu'à regarder et à utiliser les micro-outils web. |
| Pas d'API Nano Banana | Génération à la main dans l'appli Gemini : monuments un par un, détails et personnages par **planches** de 9 éléments (ou 4 poses) déposées dans `inbox/`, découpées et vectorisées par script. |
| Louis ne « peint » pas non plus | Le premier `layout.json` est généré automatiquement (rues OSM accrochées à la grille, îlots grossis, rues élargies) ; Louis ne fait que corriger des cases en cliquant. |
| Le module `bpy` n'embarque pas l'export SVG Freestyle | À résoudre en fiche 001 : extension Freestyle SVG, ou export SVG du line art Grease Pencil, ou vectorisation du PNG (potrace). |
| Les derniers 10 % prennent 90 % du temps | Le temps « main » est budgété (phase 5) et c'est là que va le charme. |
| Claude Code + GitHub | Une fiche `tasks/` par étape, outils en ligne de commande d'abord, un paramètre changé par itération. |

## Phase 0 — Décisions (fichier `DECISIONS.md`, une page)

- Format papier : 110 × 75 cm, quadrillage A–G / 1–4 en marge.
- Projection : isométrique vraie (30° sur le papier), orientation choisie une fois pour toutes.
- Trait : noir, épaisseur unique, aucune hachure, aucun aplat.
- Échelle : 1 case = 1 cm ; personnage 1 case ; voiture 2 × 1 ; immeuble ordinaire 4–8 cases de côté, 2–3 niveaux ; rue 3–5 cases ; place 15–25 cases.
- Périmètre : place Jean-Jaurès, jardin et palais de l'Évêché, cathédrale Saint-Benoît, l'Agout avec les maisons sur l'eau, 4–5 rues nommées. Tout le reste est inventé ou omis.
- Liste des 5–6 monuments et des 8–10 lieux « à histoires » (café, marché, rugby, lycée…).

**Porte :** le fichier existe et n'a pas changé depuis une semaine.

## Arborescence du repo

```
micromacro-castres/
  DECISIONS.md
  tasks/                 une fiche par étape, numérotée
  tools/
    layout-editor/       phase 1 — peindre la grille (web, un fichier html)
    placer/              phase 5 — placer sprites et personnages (web)
  pipeline/
    01_layout_to_blocks.py   layout.json → blocks.json (volumes)
    02_build_blender.py      blocks.json → scène + rendu (blender -b)
    03_assemble_svg.py       squelette + monuments + calques → carte.svg
  data/
    fond_castres.png     carte réelle en fond de l'éditeur
    layout.json
    blocks.json
  library/
    monuments/           SVG, un par monument
    details/             SVG, un par détail, nommés (chat_01.svg, terrasse_03.svg…)
    characters/          SVG, un par personnage et par pose
    catalog.json         id, fichier, taille en cases, tags
  layers/
    details.json         placements (id, x, y, miroir)
    characters.json
  cases/                 les enquêtes (markdown)
  out/                   rendus, jamais versionnés
```

## Phase 1 — Le plan de jeu (`tools/layout-editor`)

Un seul fichier HTML, fait par Claude Code. Une grille (largeur × hauteur en cases, ex. 100 × 68 pour laisser les marges), la carte réelle de Castres en fond semi-transparent, et un pinceau par type de case :

`rue`, `place`, `ilot`, `parc`, `eau`, `quai`, `monument:<nom>`, `vide`.

Options utiles : remplissage au seau, ligne droite (les rues), export/import `layout.json`, compteur de cases par type.

Format `layout.json` :
```json
{ "cols": 100, "rows": 68, "cell_cm": 1.0,
  "cells": "rrrrIIIIrr...",            // une lettre par case, ligne par ligne
  "legend": {"r":"rue","I":"ilot","p":"place","P":"parc","w":"eau","q":"quai",".":"vide"},
  "monuments": [{"id":"saint-benoit","x":40,"y":12,"w":10,"h":16}],
  "labels": [{"text":"Place Jean-Jaurès","x":50,"y":30}] }
```

**Brouillon automatique d'abord** (`pipeline/00_osm_to_layout.py`) : lit `data/castres.osm`, accroche les rues principales aux deux axes de la grille (angles arrondis à 0°/90°), pose les îlots entre elles avec une largeur de rue minimale de 4 cases, place la place, le jardin, l'Agout et les rectangles des monuments d'après `DECISIONS.md`. Louis ouvre ce brouillon dans l'éditeur et corrige.

Règles en corrigeant : rues ≥ 3 cases ; aucun îlot > 12 cases de côté ; un monument n'a rien d'important « derrière » lui dans le sens de la caméra (le bas et la droite de l'image, pour l'orientation choisie) ; au moins un tiers de la surface est rue/place/parc.

**Porte :** `layout.json` imprimé en couleurs à l'échelle A3, posé à côté de la carte MicroMacro, proportions comparables à l'œil.

## Phase 2 — Volumes (`pipeline/01_layout_to_blocks.py`)

Sans IA, déterministe, graine fixe. Pour chaque îlot (composante de cases `I`) :
- découpage en 1 à 3 rectangles (algorithme simple : plus grand rectangle inscrit, puis le reste) ;
- retrait d'une demi-case sur chaque bord (trottoir) ;
- niveaux 2 ou 3 (tirage pondéré), plafond 3 ;
- toit : plat par défaut ; 2 pans si petit rectangle ; 30 % des toits plats reçoivent une « terrasse jouable » (garde-corps) ;
- motif de fenêtres : carré / haute / vitrine / arcade ;
- monuments : rectangle réservé, hauteur fixée dans le layout, marqué `landmark`.

Sortie `blocks.json` : liste de boîtes `{x, y, w, h, levels, roof, motif, kind}` en cases, plus rues, places, parcs, eau, arbres (grille dans les parcs + rangées sur la place).

**Porte :** un rendu 2D de contrôle (PNG vu du dessus) qui ressemble au layout.

## Phase 3 — Rendu (`pipeline/02_build_blender.py`)

`blender -b -P 02_build_blender.py -- blocks.json out/ 4000`

- 1 case = 1 m dans Blender (arbitraire) ;
- boîtes, toits, fenêtres flottantes (quads devant la façade), arbres = boule sur tronc, rues = deux polygones plats (bord + trottoir), eau = polygone avec 2–3 lignes de vaguelettes, place = dallage (grille de lignes fines) ;
- caméra orthographique, rotation (54,7356°, 0, orientation) ;
- Cycles CPU, 1 échantillon, matériau émission blanc, monde blanc, vue « Standard » ;
- Freestyle : silhouette + arête + bord, lignes cachées supprimées, épaisseur 1,2–1,5 px ;
- export SVG via l'add-on Freestyle SVG, découpe aux lignes cachées activée.

Itération : un seul paramètre à la fois (épaisseur, orientation, hauteur des niveaux, taille des fenêtres).

**Porte :** impression A3 à côté de la carte MicroMacro. Question unique : « est-ce une carte MicroMacro vide ? » Si non, retour phase 1 ou 3, jamais plus loin.

## Phase 4 — Monuments (`library/monuments/`)

Pour chaque monument : on rend sa boîte seule (même caméra) en PNG, on la donne à Nano Banana avec le prompt de style (voir REF_01) et la consigne « dessine [le monument] à la place de cette boîte, même angle, même trait, fond blanc, sans ombre ». Quatre sorties, on garde une, on vectorise (potrace/Inkscape en ligne de commande), on l'enregistre sous `library/monuments/<id>.svg` avec la même taille que la boîte.

Si deux tentatives ratent : commande à un illustrateur freelance, avec le rendu de la boîte et REF_01 comme brief. Budget indicatif : quelques centaines d'euros pour 5–6 dessins.

**Porte :** les 5–6 SVG remplacent leurs boîtes dans `03_assemble_svg.py` sans décalage.

## Phase 5 — Détails et personnages (le cœur du charme)

1. **Bibliothèque.** Une liste de 150–250 détails et 40–60 personnages (avec 2–4 poses chacun) écrite d'abord en texte, dans un tableau (`library/liste.md`). Génération par **planches** dans l'appli Gemini : 9 détails par image (grille 3 × 3, fond blanc, bien séparés) ou un personnage en 4 poses ; kit de style (`STYLE.md`) joint à chaque demande. Les PNG vont dans `inbox/` ; `pipeline/04_sheets.py` découpe, vectorise (potrace), normalise l'épaisseur du trait, redimensionne à la taille catalogue et remplit `catalog.json`. Aucune retouche : on regénère la planche.
2. **Placeur** (`tools/placer`). Un HTML qui affiche `carte.svg` en fond, la bibliothèque en palette, et permet de glisser, dupliquer, retourner, supprimer ; export `layers/details.json` et `layers/characters.json`. Zoom fluide obligatoire (la carte est grande).
3. **Assemblage** (`03_assemble_svg.py`) : squelette + monuments + calques → `carte.svg` + PNG d'épreuve.

Budget de temps assumé : c'est la phase la plus longue. Elle se fait par quartiers (un quartier par soirée), pas par types de détails.

**Porte :** un quartier terminé imprimé en A4 à l'échelle 1:1, lisible à la loupe fournie avec MicroMacro.

## Phase 6 — Enquêtes

Écriture des histoires avant de placer les personnages qui en dépendent (les personnages d'enquête sont placés en dernier, sur leur parcours). Cartes d'indices au format MicroMacro (image du lieu + coordonnées). Test avec 2–3 personnes qui ne connaissent pas la carte.

## Fiches `tasks/` (ordre de création)

```
001_decisions.md           rédiger DECISIONS.md
002_layout_editor.md       l'éditeur de grille
003_layout_castres.md      peindre le premier layout (par Louis)
004_layout_to_blocks.md    volumes + rendu de contrôle 2D
005_build_blender.md       scène + Freestyle + SVG
006_print_check.md         impression A3, comparaison, décisions de réglage
007_monument_pipeline.md   boîte → Nano Banana → SVG, pour un monument test
008_library_list.md        le tableau des détails et personnages
009_generate_library.md    génération + vectorisation en série
010_placer.md              l'outil de placement
011_assemble.md            assemblage final
012_cases.md               format des enquêtes
```

Chaque fiche : objectif en une phrase, entrées, sorties, critère de réussite vérifiable, ce qui est hors périmètre.
