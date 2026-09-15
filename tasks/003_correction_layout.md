# 003 — Correction du plan de jeu et porte A3

## Objectif
Passer du brouillon automatique (`data/layout.json`, fiche 002) à un plan de jeu corrigé à la main par Louis, validé par le script de contrôle, et imprimé en couleurs à l'échelle A3 pour la porte de la phase 1 (« proportions comparables à la carte MicroMacro, à l'œil »).

## Entrées
- `data/layout.json` : brouillon du cœur en portrait (71 × 106, facteur 0,17, −5,5°), réseau réel trié, monuments à leur emprise réelle + 30 %
- `data/fond_castres_grille.png` : fond OSM aligné sur la grille (x = 0, y = 0, largeur 71)
- `tools/layout-editor/index.html`, `pipeline/check_layout.py`, `pipeline/00d_layout_print.py`
- `DECISIONS.md` : échelles, monuments, lieux à histoires

## Ce que le brouillon laisse à décider (à arbitrer par Louis dans l'éditeur)
- Les rectangles de monuments sont les boîtes englobantes d'emprises réelles parfois en L (Évêché et jardin se chevauchent à l'affichage, pas dans les cases).
- Les 31 îlots de moins de 4 cases de côté sont marqués `m` (maison unique à 2 niveaux) ; à vérifier un par un.
- Les voies repoussées au bord des monuments (jardin : 63 cases) sont à relire.

## Étapes
1. **Louis, dans l'éditeur** : ouvrir `data/layout.json`, charger le fond, corriger quartier par quartier : voies manquantes ou en trop, coudes mal placés, rectangles des monuments (outil Monument : tracer, saisir id et niveaux), cases `m` à confirmer ou à fusionner. Poser un label par lieu à histoires (marché, café, embarcadère, collège, garage, boulangerie, chantier…). Exporter, déposer dans `data/layout.json`, commiter.
2. **Claude Code** : `python3 pipeline/check_layout.py data/layout.json` doit passer sans erreur ; il vérifie la présence des 7 monuments attendus et compte les cases `m` et les labels.
3. **Claude Code** : `python3 pipeline/00d_layout_print.py` produit `out/layout_A3.png` (A3 portrait, 297 × 420 mm à 300 dpi, 1 case ≈ 3,5 mm) et `out/layout_A3.pdf`, avec légende, marges 1–4 / A–G et monuments hachurés. Posé à côté de la carte MicroMacro, les deux sont dans le même sens.
4. **Louis** : imprimer l'A3 à 100 %, poser à côté de la carte MicroMacro, répondre par oui ou non à la question « est-ce que ça se compare : rues, îlots, place, rivière ? ». Si non, retour à l'étape 1 avec la liste des quartiers à revoir.

## Critère de réussite
`check_layout.py` accepte `data/layout.json` avec les 7 monuments présents (saint-benoit, eveche, jardin-eveche, theatre, maisons-agout, pont-vieux, pont-neuf), aucune case vide (`.`), au moins 8 labels de lieux à histoires ; `out/layout_A3.pdf` imprimé et jugé « comparable » par Louis. Le pourcentage de vide n'est qu'une information.

## Hors périmètre
Les volumes (fiche 004, `01_layout_to_blocks.py`), tout rendu Blender, Gemini.
