# Éditeur de grille (fiche 002, partie B)

`index.html` : un seul fichier, sans serveur ni réseau. Double-cliquer dessus
(Safari ou Chrome) suffit.

## Usage

1. **Ouvrir layout.json** (ou glisser le fichier sur la grille). « Nouveau 106 × 71 » crée une grille vide.
2. **Image de fond** : glisser `data/fond_castres.png` (ou le choisir). Régler l'opacité,
   le décalage X / Y et la largeur en cases pour l'aligner sur la grille ; la transparence
   des cases se règle à part. Ces réglages sont mémorisés dans le JSON exporté (`background`).
3. **Peindre** : choisir un type (clic dans la liste ou touche `r I p P w q .`), puis
   pinceau (`B`, clic ou glisser ; `Maj`+clic = ligne droite depuis le dernier point),
   rectangle (`E`), seau (`G`).
4. **Monument** (`M`) : tracer un rectangle, saisir l'id et le nombre de niveaux.
   Cliquer un monument existant pour le modifier ou le supprimer.
5. **Label** (`T`) : cliquer pour poser un texte ; la liste à gauche permet de l'éditer.
6. **Exporter layout.json** (`⌘S`) : le fichier est téléchargé, à déposer dans `data/`.

Navigation : molette ou deux doigts = déplacer, `⌘`+molette ou pincer = zoom,
`+` / `−` / `0` (ajuster), `H` ou espace enfoncé = main. `⌘Z` / `⇧⌘Z` = annuler / rétablir.

Le panneau affiche le nombre de cases par type, la part rues + places + parcs
(objectif ≥ 33 %) et le nombre de cases de rue de moins de 3 de large (surlignées
en rouge). Les mêmes chiffres sont calculés par `pipeline/check_layout.py`.

## Fichiers

- `index.html` — l'éditeur
- `make_exemple.py` — fabrique `exemple_layout.json`, un layout synthétique 106 × 71
  (contient volontairement une rue de 2 cases pour tester l'alerte)
- `exemple_layout.json` — pour tester l'éditeur sans le brouillon réel
- `test_editor.py` — test automatisé Playwright : charge l'exemple, modifie 20 cases,
  vérifie rectangle / seau / ligne / annuler / monument, exporte et valide avec
  `check_layout.py`

```
python3 tools/layout-editor/make_exemple.py
python3 tools/layout-editor/test_editor.py --shots out/editor
```
