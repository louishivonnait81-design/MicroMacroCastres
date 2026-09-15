# 006 — Éditeur autonome : Louis corrige le plan à la main

## Objectif
Donner à Louis un seul fichier HTML, sans installation ni glisser-déposer, qui s'ouvre déjà chargé avec le plan figé et le fond OSM aligné sur la grille, pour reprendre le plan case par case après avoir vu la 3D.

## Entrées
- `data/layout.json` : plan figé le 18/09
- `data/fond_castres_grille.png` : fond OSM aligné (x = 0, y = 0, largeur 71 cases)
- `tools/layout-editor/index.html` : l'éditeur (inchangé dans son usage habituel)

## Étapes
1. `python3 pipeline/03_editeur_autonome.py` → `out/editeur_castres.html` (1,5 Mo, plan + fond embarqués en base64).
2. Louis télécharge le fichier et l'ouvre d'un double clic dans Safari ou Chrome. Le plan, les 8 monuments, les 19 labels et le fond s'affichent tout seuls.
3. Louis corrige : outils Crayon `C`, Rectangle `E`, Seau `G`, Monument `N`, Label `T`, Main `H` ; types de case aux touches `r` rue, `b` boulevard, `I` îlot, `m` maison, `p` place, `P` parc, `w` eau, `q` quai. `Cmd + Z` annule, `0` recadre, `+` / `-` zooment, le curseur « Cases » rend le fond plus ou moins visible.
4. Louis clique « Exporter layout.json » (ou `Cmd + S`) et redonne le fichier à Claude Code.
5. Claude Code rejoue les fiches 004 et 005 par-dessus, sans jamais régénérer le plan depuis OSM.

## Ce que la 3D a montré, à regarder en priorité
- Les maisons sur l'Agout sont hachées en 16 morceaux : les fusionner en quelques longues bandes.
- Les îlots au sud-est sont énormes et donnent des barres de 25 cases de long : les couper par une venelle ou les retailler.
- Le chantier, le garage et l'embarcadère sont des labels devinés : les poser au bon endroit.

## Critère de réussite
Le fichier s'ouvre hors ligne, plan et fond chargés, aucune erreur JavaScript ; Louis exporte un `layout.json` que `python3 pipeline/check_layout.py` accepte.

## Hors périmètre
Toute régénération depuis OSM, les volumes et le rendu (fiches 004 et 005), le choix définitif de la caméra.
