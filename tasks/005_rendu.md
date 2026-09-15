# 005 — Rendu isométrique Blender

## Objectif
Rendre `data/blocks.json` (fiche 004) en une image isométrique noir et blanc en ligne claire (Freestyle, sans ombre), pour juger d'un coup d'œil si la ville « ressemble » à une carte MicroMacro, et choisir l'orientation et l'inclinaison de la caméra.

## Entrées
- `data/blocks.json` : volumes en unités « case » (1 case = 1 unité, 1 niveau = 1 unité)
- `bpy` 5.0.1 installé comme module Python (`python3 -m pip install bpy`) ; Blender en ligne de commande marche aussi

## Étapes
1. `python3 pipeline/02_build_blender.py data/blocks.json out/rendu 1800 [orientation] [inclinaison]`
   - orientation : angle de la caméra autour de la verticale (45 = vue depuis le sud-ouest, rues à 45° ; 15 = rues presque droites)
   - inclinaison : angle de la caméra par rapport à la verticale (54,7 = vraie isométrie ; 38 = vue plus plongeante, façades plus courtes, image plus haute)
   - sorties : `out/rendu/castres[_ori_inc].png` et `.blend`
2. Regarder l'image : rues blanches bordées d'un trait, façades avec fenêtres selon le motif, vitrines au rez-de-chaussée, terrasses avec garde-corps, toits à 2 pans sur les maisons uniques, clocher, fronton du théâtre, Agout en vaguelettes, arbres en boules.
3. Louis choisit orientation + inclinaison (voir « Constat » ci-dessous). La valeur choisie devient `ISO_TURN` / `ISO_TILT` dans le script.
4. Rendu à la taille d'impression : 75 × 110 cm à 300 dpi ≈ 8 860 px de large (`largeur_px = 8860`) ; l'épaisseur de trait `LINE_THICKNESS` se règle ensuite à l'œil sur un tirage A4 d'un détail.

## Comparateur d'angles (fiche 005 bis)
`python3 pipeline/04_comparateur_angles.py 900` rend 20 combinaisons (orientations 0 / 10 / 20 / 30 / 45°, inclinaisons 25 / 35 / 45 / 54,7°), **chacune cadrée dans la feuille 75 × 110 portrait**, et assemble `out/angles_castres.html` : un fichier à ouvrir d'un double clic, deux curseurs, le taux de remplissage de la feuille et le tableau complet. Le mode feuille est aussi accessible directement : 6e argument de `02_build_blender.py` = largeur / hauteur de la feuille (0.682), ou `libre` pour que l'image épouse la ville.

Remplissage de la feuille, en pourcentage :

| inclinaison \ orientation | 0° | 10° | 20° | 30° | 45° |
|---|---|---|---|---|---|
| 25° | 96 | 84 | 77 | 71 | 64 |
| 35° | 88 | 77 | 70 | 65 | 58 |
| 45° | 77 | 68 | 62 | 57 | 51 |
| 54,7° | 65 | 57 | 52 | 48 | 43 |

## Constat (18/09)
La vraie isométrie (inclinaison 54,7°) écrase la profondeur d'un facteur 0,58 : le plan portrait 71 × 106 donne toujours une **image paysage** (1,6:1 à 45°, 1,3:1 à 20°). Pour remplir une feuille 75 × 110 **portrait**, il faut une vue plus plongeante : à 38° d'inclinaison et 15° d'orientation, l'image est au format 1:1,04 (presque portrait) et ressemble davantage à la carte MicroMacro (façades courtes, toits bien visibles). Trois rendus sont proposés à Louis : 45°/54,7°, 20°/54,7° et 15°/38°.

## Critère de réussite
Un PNG de la ville entière en ligne claire, lisible, produit en moins d'une minute à 1 800 px, avec tous les objets de blocks.json ; Louis a choisi l'orientation et l'inclinaison.

## Hors périmètre
L'export SVG (add-on Freestyle SVG absent de bpy 5 ; Grease Pencil ou potrace à voir en fiche 006), les personnages et les scènes des dix lieux, les textes et labels sur l'image, la version couleur.
