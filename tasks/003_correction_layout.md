# 003 — Correction du plan de jeu et porte A3

## Objectif
Passer du brouillon automatique (`data/layout.json`, fiche 002) à un plan de jeu corrigé à la main par Louis, validé par le script de contrôle, et imprimé en couleurs à l'échelle A3 pour la porte de la phase 1 (« proportions comparables à la carte MicroMacro, à l'œil »).

## Entrées
- `data/layout.json` : la variante de découpe choisie par Louis (îlots ≤ 12, ≤ 16 ou sans découpe ; `python3 pipeline/00_osm_to_layout.py --max-block N`)
- `data/fond_castres_grille.png` : fond OSM aligné sur la grille (x = 0, y = 0, largeur 106)
- `tools/layout-editor/index.html`, `pipeline/check_layout.py`
- `DECISIONS.md` : échelles, monuments, lieux à histoires

## Étapes
1. **Louis, dans l'éditeur** : ouvrir `data/layout.json`, charger le fond, corriger quartier par quartier en suivant les règles de SQUELETTE.md : rues ≥ 3 cases ; aucun îlot > 12 cases de côté ; au moins un tiers de rue + place + parc ; rien d'important « derrière » un monument dans le sens de la caméra (bas et droite de l'image pour l'orientation par défaut). Déplacer les monuments à leur vraie place relative : théâtre au sud-ouest de la place, cathédrale puis Évêché puis jardin du nord au sud le long de l'Agout. Poser un label par lieu à histoires (marché, café, embarcadère, collège, garage, boulangerie, chantier…) pour se souvenir où ils iront. Exporter, déposer dans `data/layout.json`, commiter.
2. **Claude Code** : `python3 pipeline/check_layout.py data/layout.json` doit passer sans erreur ; ajouter au script un contrôle « aucun îlot > 12 cases de côté » (composantes 4-connexes de `I`, monuments exclus) et le nombre de labels.
3. **Claude Code** : écrire `pipeline/00d_layout_print.py` qui produit `out/layout_A3.png` (297 × 420 mm à 300 dpi, paysage, une couleur par type, monuments hachurés, marges A–G / 1–4, échelle et légende) et `out/layout_A3.pdf`. La grille entière tient sur la feuille : 1 case ≈ 3,8 mm.
4. **Louis** : imprimer en couleurs, poser à côté de la carte MicroMacro, répondre par oui ou non à la question « rues aussi larges, îlots aussi petits ? ». Si non, retour à l'étape 1 avec la liste des quartiers à revoir.

## Critère de réussite
`check_layout.py` accepte `data/layout.json` avec : part rue + place + parc ≥ 33 %, zéro case de rue < 3, zéro îlot > 12 cases, les 7 monuments présents (saint-benoit, eveche, jardin-eveche, theatre, maisons-agout, pont-vieux, pont-neuf) et au moins 8 labels de lieux à histoires ; `out/layout_A3.pdf` imprimé et jugé « comparable » par Louis.

## Hors périmètre
Les volumes (fiche 004, `01_layout_to_blocks.py`), tout rendu Blender, Gemini.
