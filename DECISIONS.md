# DECISIONS — MicroMacro-Castres

Une page. Ce qui est écrit ici ne se rediscute pas dans les fiches `tasks/`. Arrêté le 15/09/2026, périmètre et format révisés le 17/09/2026.

## Objet

Un jeu de type MicroMacro : une grande carte isométrique noir et blanc du vieux Castres, compressé mais fidèle dans son tracé, sur laquelle des personnages racontent des histoires que les joueurs reconstituent à la loupe.

## Format

- Papier : 75 × 110 cm, **portrait**, comme la carte MicroMacro posée sur la table. Marge de 2 cm avec quadrillage 1–4 (petit côté) / A–G (grand côté).
- Grille de travail : 1 case = 1 cm papier. Zone dessinée : **71 × 106 cases** (71 colonnes, 106 lignes).
- Projection : axonométrique orthographique. **Angle figé le 19/09 : orientation 10°, inclinaison 35°** (`ISO_TURN = 10`, `ISO_TILT = 35` dans `pipeline/02_build_blender.py`). L'isométrie vraie (inclinaison 54,7°) a été écartée : elle couche la ville en paysage et ne remplit que 57 % d'une feuille portrait, contre 77 % à 35°. Les rendus sont cadrés par défaut dans la feuille 75 × 110.
- Trait : noir, une seule épaisseur (1,2–1,5 px à 4000 px de large ; ~0,25 mm au tirage), aucune hachure, aucun aplat, aucune ombre.
- Fichiers finaux : SVG (calques : squelette, monuments, détails, personnages, cadre) + PNG 300 dpi.

## Échelles (en cases) — ce qui ne se compresse pas

| Élément | Taille |
|---|---|
| Personnage debout | 1 de haut — **jamais réduit** |
| Voiture | 2 × 1 |
| Arbre (boule) | 1,5–2 de diamètre |
| Agout | largeur réelle, 6 cases |
| Niveau d'immeuble | 1 de haut |
| Voie | venelle 1, ruelle 2, rue 3, rue nommée 4, boulevard / quai 6–8 |
| Place Jean-Jaurès | emprise réelle, 19 × 8 à 0,17 |

## Compression — ce qui se compresse

Le périmètre est le **cœur** de la ville (ci-dessous), pas le périmètre étendu. Règle : on garde le tracé réel (voies, îlots, monuments, rivière) et on compresse les longueurs d'un facteur unique. Facteur retenu (17/09) : **0,170 case par mètre, soit 1 case ≈ 5,9 m**. La grille couvre 418 × 624 m.

- Toutes les voies nommées dans OSM sont gardées, avec leurs connexions ; sont écartées d'office les trottoirs, passages piétons, voies de service sans nom, `path`, `cycleway`, escaliers sans nom et doublons de trottoir. Un Castrais doit pouvoir suivre n'importe quel trajet de la vraie ville sur la carte.
- Largeur selon le caractère : venelle 1 case, rue ordinaire 2, avenue et voie primaire 3, les cinq rues nommées 4, boulevards Léon Bourgeois / Miredames / Henri Sizaire et quais 5 (plantés). Pas d'escalier de cases : au plus un coude à angle droit toutes les 8 cases.
- Tout ce qui n'est pas voie, place, parc ou eau est îlot, plein. Un îlot de moins de 4 cases de côté est une maison unique à 2 niveaux.
- L'Agout est à sa largeur réelle (6 cases à 0,17). Le long de l'Agout il y a soit un trottoir (bande de quai), soit des bâtiments, jamais que la route : les voies ne recouvrent pas la bande de rive, et les maisons sur l'Agout (les Arcades, face à la façade est de la place) ont les pieds dans l'eau. Le quai des Jacobins, passage entre la façade est de la place et les Arcades, fait 2 cases ; les autres quais gardent 5 cases (choix du 17/09, option A).
- Les monuments sont à leur position réelle, à leur emprise réelle OSM compressée agrandie de 30 % dans les îlots voisins uniquement, jamais sur une voie. Une voie ne traverse pas un monument : les venelles et ruelles sous l'emprise réelle disparaissent, les autres voies sont repoussées au bord.
- Le personnage reste 1 case : c'est l'échelle réelle de MicroMacro.
- La part de vide n'est qu'une information.

## Périmètre

Le cœur de Castres, en portrait : un rectangle de 418 × 624 m tourné de −5,5° (place Jean-Jaurès et rue Sabatier droites), centré sur les neuf éléments obligatoires puis décalé de 20 m vers l'ouest pour prendre la rue Chambre de l'Édit. Centre 43.60423 N, 2.24289 E ; coins NW 43.60719 N, 2.24068 E, NE 43.60683 N, 2.24584 E, SE 43.60126 N, 2.24510 E, SW 43.60162 N, 2.23994 E.

Éléments obligatoires, tous dans le cadre : place Jean-Jaurès, cathédrale Saint-Benoît, palais de l'Évêché et son jardin entier, théâtre, l'Agout avec les maisons sur l'eau, Pont Vieux (9 cases de marge) et Pont Neuf, rue Villegoudou, église Saint-Jacques de Villegoudou.

Rues nommées (largeur 4) : rue Sabatier, rue Frédéric Thomas / Victor Hugo, rue de l'Hôtel de Ville, rue Villegoudou, quai des Jacobins. Les autres voies existent sur la carte à leur largeur de caractère mais ne sont pas nommées.

Lieux à histoires (10) :
1. le marché sur la place Jean-Jaurès
2. une terrasse de café sur la place (Le Glacier, angle nord-ouest ; le théâtre n'est pas sur la place)
3. le coche d'eau sur l'Agout, avec la file à l'embarcadère
4. le jardin de l'Évêché, jardiniers et promeneurs
5. les balcons des maisons sur l'Agout, linge et pêcheurs
6. une sortie de collège, rue encombrée de parents
7. un garage avec une voiture sur le pont élévateur
8. une boulangerie avec la file du samedi matin
9. un chantier de ravalement avec échafaudage
10. le rugby **dans les personnages** : supporters en maillot, joueur boueux, troisième mi-temps au café — pas de stade.

Tout ce qui n'est pas dans cette liste est simplifié ou omis. Les labels des dix lieux sont dans `data/layout.json` (★ d'après OSM, ★? devinés : embarcadère du coche d'eau, garage, chantier).

Réseau figé le 18/09 (porte de la fiche 003 passée : deux oui). Plus de régénération de `data/layout.json` sans accord de Louis.

## Monuments (emprise réelle OSM compressée, +30 % dans les îlots voisins)

| id | Nom | Emprise réelle (cases) | Emprise +30 % | Hauteur |
|---|---|---|---|---|
| saint-benoit | cathédrale Saint-Benoît | 46 | 60 | 3 + clocher 6 |
| eveche-mairie | palais de l'Évêché = hôtel de ville et musée Goya (OSM : « Hôtel de Ville de Castres ») | 65 | 84 | 3 |
| jardin-eveche | jardin de l'Évêché | 300 | 390 | — |
| theatre | théâtre municipal (à sa vraie position, près de la rue de l'Évêché, au sud-ouest du jardin) | 31 | 40 | 3 + fronton |
| saint-jacques | église Saint-Jacques de Villegoudou | 30 | 39 | 3 + clocher |
| maisons-agout | maisons sur l'Agout (rive gauche entre les ponts) | 58 | 58 | 3 |
| pont-vieux, pont-neuf | Pont Vieux et Pont Neuf | voies de 4 cases d'une rive à l'autre | — | — |

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
