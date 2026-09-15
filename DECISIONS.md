# DECISIONS — MicroMacro-Castres

Une page. Ce qui est écrit ici ne se rediscute pas dans les fiches `tasks/`. Arrêté le 15/09/2026.

## Objet

Un jeu de type MicroMacro : une grande carte isométrique noir et blanc du vieux Castres, compressé mais fidèle dans son tracé, sur laquelle des personnages racontent des histoires que les joueurs reconstituent à la loupe.

## Format

- Papier : 110 × 75 cm, paysage. Marge de 2 cm avec quadrillage A–G / 1–4 comme sur MicroMacro.
- Grille de travail : 1 case = 1 cm papier. Zone dessinée : 106 × 71 cases.
- Projection : isométrique vraie (angles à 30° sur le papier), orthographique. Orientation `ISO_TURN = 45°` par défaut ; fixée après la fiche 006.
- Trait : noir, une seule épaisseur (1,2–1,5 px à 4000 px de large ; ~0,25 mm au tirage), aucune hachure, aucun aplat, aucune ombre.
- Fichiers finaux : SVG (calques : squelette, monuments, détails, personnages, cadre) + PNG 300 dpi.

## Échelles (en cases) — ce qui ne se compresse pas

| Élément | Taille |
|---|---|
| Personnage debout | 1 de haut — **jamais réduit** |
| Voiture | 2 × 1 |
| Arbre (boule) | 1,5–2 de diamètre |
| Niveau d'immeuble | 1 de haut |
| Rue | 3 minimum, 5 pour les boulevards |
| Place Jean-Jaurès | 18–24 |

## Compression — ce qui se compresse

Le périmètre est **étendu** et ne tient pas à l'échelle réelle. Règle : on garde le tracé réel (position relative des rues, des îlots, des monuments, de la rivière) et on compresse les **longueurs** d'un facteur unique. Facteur retenu (fiche 002) : **0,097 case par mètre, soit 1 case ≈ 10 m**. Le périmètre de 927 × 735 m tient ainsi dans 106 × 71 cases ; la marge de 16 cases en largeur va à l'est, sur Villegoudou.

- Un îlot réel devient un à deux immeubles de 4–8 cases.
- Seuls les boulevards, les rues principales et les cinq rues nommées sont conservés ; les venelles et impasses sont omises.
- Les rues conservées font 4 cases (6 pour les boulevards). Les rues ne descendent jamais sous 3 cases.
- Le personnage reste 1 case : c'est l'échelle réelle de MicroMacro, où les personnages sont dix fois trop grands par rapport aux bâtiments.

- Hauteurs : **3 niveaux partout**, monuments compris sauf clocher et théâtre. Pas d'exception.
- Gros bâtiments (cathédrale, Évêché, théâtre) : emprise réduite à 2–3 immeubles ordinaires, silhouette conservée.

Hiérarchie de détail : bâtiments pauvres (boîtes + fenêtres), rues et arbres minimaux, monuments moyens, tout le détail dans les personnages et les petits objets.

## Périmètre

Rive gauche : du bd Léon Bourgeois à l'Agout, du bd Miredames au bd Henri Sizaire (place Jean-Jaurès, cathédrale, Évêché et jardin, théâtre). Rive droite : le quartier Villegoudou et le quai, jusqu'à la première rue parallèle à l'Agout. Deux ponts.

Rues nommées (réseau, à confirmer sur place) : rue Sabatier, rue Frédéric Thomas / Victor Hugo, rue de l'Hôtel de Ville, rue Villegoudou, quai des Jacobins. Les autres rues existent sur la carte mais ne sont pas nommées.

Lieux à histoires (10) :
1. le marché sur la place Jean-Jaurès
2. une terrasse de café sur la place, face au théâtre
3. le coche d'eau sur l'Agout, avec la file à l'embarcadère
4. le jardin de l'Évêché, jardiniers et promeneurs
5. les balcons des maisons sur l'Agout, linge et pêcheurs
6. une sortie de collège, rue encombrée de parents
7. un garage avec une voiture sur le pont élévateur
8. une boulangerie avec la file du samedi matin
9. un chantier de ravalement avec échafaudage
10. le rugby **dans les personnages** : supporters en maillot, joueur boueux, troisième mi-temps au café — pas de stade.

Tout ce qui n'est pas dans cette liste est simplifié ou omis.

## Monuments (6, boîtes réservées dans la grille)

| id | Nom | Emprise (cases, après compression) | Hauteur |
|---|---|---|---|
| saint-benoit | cathédrale Saint-Benoît | ~10 × 14 | 3 niveaux + clocher 6 |
| eveche | palais de l'Évêché (hôtel de ville / musée Goya) | ~12 × 7 | 3 |
| jardin-eveche | jardin de l'Évêché | ~14 × 10 | — |
| theatre | théâtre municipal | ~7 × 6 | 3 + fronton |
| maisons-agout | maisons sur l'Agout (rangée) | ~20 × 4 | 3 |
| ponts | Pont Vieux et Pont Neuf | 2 × (6 × 3) | — |

## Ce qu'on ne fait pas

- Pas d'IA sur la carte entière, jamais. L'IA ne voit que des éléments isolés.
- Pas de retouche d'image IA : on regénère.
- Pas de fidélité métrique, mais fidélité du tracé.
- Pas de couleur. Pas de stade.
- Pas de texte sur la carte hors enseignes.

## Outils

- Repo GitHub `micromacro-castres`, Claude Code en version cloud connectée au repo.
- Blender = module Python `bpy` (Python 3.11) dans l'environnement Claude Code.
- Images IA : appli Gemini, à la main, déposées dans `inbox/`.
- Vectorisation : potrace. Édition manuelle : aucune (micro-outils web dans `tools/`).
