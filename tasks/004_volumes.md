# 004 — Volumes : du plan de jeu aux boîtes

## Objectif
Transformer le plan figé (`data/layout.json`) en volumes simples (`data/blocks.json`) prêts pour Blender, selon des règles fixes et un tirage aléatoire reproductible, avec un PNG de contrôle vu du dessus où chaque boîte porte sa hauteur.

## Entrées
- `data/layout.json` : réseau figé le 18/09 (plus de régénération sans accord de Louis)
- `data/streets_index.json` : liste des voies avec leurs cases (pour savoir quelles cases bordent une rue nommée ou une venelle)
- `DECISIONS.md` : monuments, place, jardin

## Règles (Louis, 18/09)
- Îlot ordinaire : 1 à 2 boîtes (plus grand rectangle inscrit, puis le suivant), 2 ou 3 niveaux (3 max partout).
- Maison unique `m` : 1 boîte, 2 niveaux, toit à 2 pans.
- Toute boîte qui borde une venelle de 1 case : 2 niveaux max.
- Toit plat par défaut ; 30 % des toits plats ont une terrasse jouable (garde-corps).
- Rez-de-chaussée « vitrine » sur les rues nommées et tout autour de la place ; ailleurs motifs carré / haute / arcade tirés au sort (graine fixe 42).
- Monuments : boîte à leur emprise, 3 niveaux ; clocher de 6 niveaux (2 × 2 cases) sur la cathédrale ; fronton à 2 pans sur la façade nord du théâtre.
- Jardin = parc avec allées en croix et arbres en grille ; place = dallage avec deux rangées de platanes ; boulevards plantés d'arbres d'alignement.

## Écarts par rapport aux règles (à valider par Louis)
- Les deux rectangles laissaient 484 cases d'îlot non bâties (les bords des îlots sont en escalier à −5,5°). Le script autorise une **3e boîte** quand le reste offre encore un rectangle d'au moins 6 cases (11 îlots concernés) ; ce qui reste (294 cases, surtout des bandes d'une case le long des rues) devient du **trottoir**. Pour revenir strictement à 2 boîtes : `ANNEX_MIN = 10**9` dans le script.

## Étapes
1. `python3 pipeline/01_layout_to_blocks.py data/layout.json data/blocks.json out/blocks_preview.png`
2. Regarder `out/blocks_preview.png` : chiffre = niveaux, T = terrasse, ^ = 2 pans, v = vitrine, cercles = arbres, violet = monuments.
3. Vérifier `data/blocks.json` : GeoJSON en unités « case » (1 case = 1 unité, 1 niveau = 1 unité en hauteur), `features[].properties.kind` ∈ volume / landmark / road / sidewalk / water / park / place / tree, `bounds = [0, 0, 71, 106]`.

## Critère de réussite
Aucune boîte de plus de 3 niveaux hors clocher ; aucune boîte de 3 niveaux au bord d'une venelle ; toutes les boîtes autour de la place et le long des rues nommées en vitrine ; 8 monuments présents (dont le jardin en parc) ; PNG de contrôle lisible. Obtenu : 95 boîtes + 20 boîtes de monuments + clocher + fronton, 25 vitrines, 90 arbres.

## Hors périmètre
Le rendu (fiche 005), les retouches à la main du plan, toute régénération de `data/layout.json`.
