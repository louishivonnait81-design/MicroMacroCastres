# Prompt de lancement — à coller dans Claude Code (cloud), repo connecté

## Message 1 : cadrage

```
Tu travailles sur le projet MicroMacro-Castres. Avant toute action, lis dans cet ordre :
SQUELETTE.md, DECISIONS.md, STYLE.md, puis tasks/001_environnement.md et tasks/002_layout_editor.md.

Règles de travail, non négociables :
1. Une fiche tasks/ à la fois, dans l'ordre. Tu ne commences pas une fiche tant que le critère de réussite de la précédente n'est pas vérifié par toi, avec preuve (image rendue, fichier produit, commande qui passe).
2. Tout ce que tu construis est d'abord un outil en ligne de commande testable seul (`make <cible>` ou `python pipeline/xx.py`), puis seulement intégré.
3. Un seul paramètre changé entre deux rendus. Chaque rendu est sauvegardé dans out/ avec un nom qui dit ce qui a changé.
4. Aucune IA d'images n'est appelée par le code. Les images IA arrivent dans inbox/, faites à la main.
5. Tu commites à la fin de chaque fiche avec un message "tasks/00X — <résumé>", et tu écris la fiche suivante (tasks/00X+1.md) au même format (Objectif / Entrées / Étapes / Critère de réussite / Hors périmètre) en te basant sur SQUELETTE.md, avant de t'arrêter.
6. Quand une décision de goût est nécessaire (orientation de la carte, épaisseur du trait, taille des fenêtres), tu produis 2 à 4 rendus côte à côte, tu les nommes, et tu t'arrêtes pour que je choisisse. Tu ne choisis pas à ma place.
7. Si quelque chose ne marche pas après trois tentatives, tu t'arrêtes et tu m'expliques en cinq lignes ce qui bloque et les options.

Commence par tasks/001_environnement.md. Confirme d'abord en trois lignes ce que tu as compris du projet, puis exécute.
```

## Message 2 : après la fiche 001 validée

```
Fiche 001 validée. Passe à tasks/002. Le fichier data/castres.osm est dans le repo ; génère le fond avec pipeline/00b_osm_to_fond.py. Le facteur de compression est celui de DECISIONS.md (0,097 case/m) ; affiche-le. Produis le brouillon, son PNG de contrôle et arrête-toi pour que je le corrige dans l'éditeur.
```

## Message 3 : à chaque nouvelle fiche

```
Fiche 00X validée [+ éventuellement : voici mes choix / corrections]. Passe à tasks/00X+1.
```

## Ce que Louis fournit, et quand

| Quand | Quoi | Où |
|---|---|---|
| avant message 1 | DECISIONS.md complété (rues, lieux à histoires, monuments) | racine |
| avant message 2 | export OSM de la zone (`castres.osm`), via `python3 pipeline/00a_fetch_osm.py` sur le Mac ou overpass-turbo.eu ; le fond `fond_castres.png` est ensuite généré par `00b_osm_to_fond.py` | data/ |
| fiche 003 | corrections du layout dans l'éditeur, export de layout.json | data/ |
| fiche 006 | verdict sur l'impression A3 et choix d'orientation / trait | en message |
| fiche 007 | images de monuments faites dans Gemini | inbox/ |
| fiche 008 | listes de détails et de personnages (library/liste.md) | library/ |
| fiche 009 | planches faites dans Gemini | inbox/ |
| fiche 010+ | placement des sprites dans le placeur, quartier par quartier | layers/ |
| fiche 012 | les enquêtes | cases/ |
