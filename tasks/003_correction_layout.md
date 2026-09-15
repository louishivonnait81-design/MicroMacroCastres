# 003 — Correction du plan de jeu et porte A3

## Objectif
Passer du brouillon automatique (`data/layout.json`, fiche 002) à un plan de jeu corrigé à la main par Louis, validé par le script de contrôle, et imprimé en couleurs à l'échelle A3 pour la porte de la phase 1 (« proportions comparables à la carte MicroMacro, à l'œil »).

## Entrées
- `data/layout.json` : brouillon du cœur en portrait (71 × 106, facteur 0,17, −5,5°), réseau réel trié, monuments à leur emprise réelle + 30 %
- `data/fond_castres_grille.png` : fond OSM aligné sur la grille (x = 0, y = 0, largeur 71)
- `tools/layout-editor/index.html`, `pipeline/check_layout.py`, `pipeline/00d_layout_print.py`
- `DECISIONS.md` : échelles, monuments, lieux à histoires

## Fait par script le 18/09 (règles de Louis)
- Voies parallèles accolées à moins d'une case fusionnées en une seule, à la largeur de la plus large (29 fusions, listées dans `out/voies_supprimees.txt`).
- Plus aucune case étrangère dans les boîtes de monuments : une voie repoussée ne peut plus entrer dans un monument déjà posé.
- Les îlots de moins de 4 cases restent des maisons uniques (lettre `m`), c'est voulu.
- Les dix lieux à histoires de DECISIONS.md sont posés en labels (préfixe ★ ; ★? = endroit deviné faute de donnée OSM : embarcadère du coche d'eau, garage, chantier).

## Étapes
1. **Louis** : imprimer l'A3 portrait, le poser à côté de la carte MicroMacro et répondre à deux questions par oui ou non : la place et les rues connues sont-elles là où on les attend ? Les rues ont-elles l'air de rues et les îlots d'îlots ? Deux oui → fiche 004. Les retouches case par case dans l'éditeur viendront plus tard, quand la 3D aura montré ce qui gêne vraiment.
2. **Claude Code** : `python3 pipeline/check_layout.py data/layout.json` doit passer sans erreur ; il vérifie la présence des 7 monuments attendus et compte les cases `m` et les labels.
3. **Claude Code** : `python3 pipeline/00d_layout_print.py` produit `out/layout_A3.png` (A3 portrait, 297 × 420 mm à 300 dpi, 1 case ≈ 3,5 mm) et `out/layout_A3.pdf`, avec légende, marges 1–4 / A–G et monuments hachurés. Posé à côté de la carte MicroMacro, les deux sont dans le même sens.
4. **Louis** : imprimer l'A3 à 100 %, poser à côté de la carte MicroMacro, répondre par oui ou non à la question « est-ce que ça se compare : rues, îlots, place, rivière ? ». Si non, retour à l'étape 1 avec la liste des quartiers à revoir.

## Critère de réussite
`check_layout.py` accepte `data/layout.json` avec les 8 monuments présents (saint-benoit, eveche-mairie, jardin-eveche, theatre, saint-jacques, maisons-agout, pont-vieux, pont-neuf), aucune case vide (`.`), au moins 8 labels de lieux à histoires ; `out/layout_A3.pdf` imprimé et jugé « comparable » par Louis. Le pourcentage de vide n'est qu'une information.

## Hors périmètre
Les volumes (fiche 004, `01_layout_to_blocks.py`), tout rendu Blender, Gemini.
