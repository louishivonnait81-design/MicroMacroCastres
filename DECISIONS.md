# DECISIONS — MicroMacro-Castres

Une page. Ce qui est écrit ici ne se rediscute pas dans les fiches `tasks/`. Les lignes marquées `[À COMPLÉTER]` sont à remplir par Louis avant la fiche 003.

## Objet

Un jeu de type MicroMacro : une grande carte isométrique noir et blanc d'un vieux Castres réinventé, sur laquelle des personnages racontent des histoires que les joueurs reconstituent à la loupe.

## Format

- Papier : 110 × 75 cm, paysage. Marge de 2 cm avec quadrillage A–G (vertical) / 1–4 (horizontal) comme sur MicroMacro.
- Grille de travail : 1 case = 1 cm papier. Zone dessinée : 106 × 71 cases.
- Projection : isométrique vraie (angles à 30° sur le papier), orthographique. Orientation : `ISO_TURN = 45°` par défaut ; changée une fois pour toutes après la fiche 006.
- Trait : noir, une seule épaisseur (1,2–1,5 px à 4000 px de large ; ~0,25 mm au tirage), aucune hachure, aucun aplat, aucune ombre, aucun dégradé.
- Fichiers finaux : SVG (calques : squelette, monuments, détails, personnages, cadre) + PNG 300 dpi.

## Échelles (en cases)

| Élément | Taille |
|---|---|
| Personnage debout | 1 de haut |
| Voiture | 2 × 1 |
| Arbre (boule) | 1,5–2 de diamètre |
| Niveau d'immeuble | 1 de haut |
| Immeuble ordinaire | 4–8 de côté, 2–3 niveaux |
| Rue | 3–5 de large |
| Place | 15–25 |
| Monument | 2–3 immeubles, jamais plus |

Hiérarchie de détail : bâtiments pauvres (boîtes + fenêtres), rues et arbres minimaux, monuments moyens, tout le détail dans les personnages et les petits objets.

## Périmètre

Un vieux Castres réinventé, pas reproduit. Lieux obligatoires :

- place Jean-Jaurès (dallage, platanes en rangées, fontaine)
- cathédrale Saint-Benoît
- palais de l'Évêché (hôtel de ville / musée Goya) et son jardin à la française
- l'Agout et les maisons sur l'eau, un pont
- 4–5 rues nommées : `[À COMPLÉTER — ex. rue Sabatier, rue de la Platé, rue Villegoudou…]`

Lieux « à histoires » (8–10) : `[À COMPLÉTER — ex. le café de …, le marché, le stade de rugby, le lycée, la gare, une boulangerie, une librairie, un garage, la piscine…]`

Tout ce qui n'est pas dans cette liste est inventé ou omis. Si ça ne tient pas dans 106 × 71 cases, on réduit le périmètre, jamais l'échelle.

## Monuments (5–6, boîtes réservées dans la grille)

| id | Nom | Emprise (cases) | Hauteur (niveaux) |
|---|---|---|---|
| saint-benoit | cathédrale Saint-Benoît | ~10 × 16 | 6 (+ clocher) |
| eveche | palais de l'Évêché | ~14 × 8 | 3 |
| jardin-eveche | jardin de l'Évêché | ~16 × 12 | — |
| maisons-agout | maisons sur l'Agout (rangée) | ~24 × 4 | 3 |
| pont | pont sur l'Agout | ~6 × 3 | — |
| `[À COMPLÉTER]` | | | |

## Ce qu'on ne fait pas

- Pas d'IA sur la carte entière, jamais. L'IA ne voit que des éléments isolés.
- Pas de retouche d'image IA : on regénère.
- Pas de fidélité cadastrale.
- Pas de couleur.
- Pas de texte sur la carte hors enseignes (les noms de rues sont dans les enquêtes, pas sur la carte).

## Outils

- Repo GitHub `micromacro-castres`, Claude Code en version cloud connectée au repo.
- Blender = module Python `bpy` (Python 3.11) dans l'environnement Claude Code. Le Mac de Louis ne rend rien.
- Images IA : appli Gemini, à la main, images déposées dans `inbox/`.
- Vectorisation : potrace. Édition manuelle : aucune (micro-outils web dans `tools/`).
