# STYLE — kit pour les générations Gemini (phases 4 et 5)

Ne sert qu'après la fiche 006 (squelette validé sur papier). Le kit se compose de trois choses : une image de référence, un prompt fixe, une planche de test.

## 1. Image de référence : `library/REF_STYLE.png`

À produire après la fiche 006 : un recadrage du rendu Blender à taille finale (environ 1200 × 800 px) avec un immeuble à 3 niveaux, un arbre, un bout de rue avec trottoir. C'est ce qui donne à l'IA l'angle et le trait. **On ne donne jamais la carte MicroMacro à l'IA** : on veut nos personnages dans notre trait, pas les siens.

## 2. Prompt fixe (à coller tel quel, en joignant REF_STYLE.png)

```
Dessin technique au trait, noir sur fond blanc pur. Copie exactement le style de l'image jointe :
- une seule épaisseur de trait, fine et régulière, comme un dessin vectoriel
- aucune ombre, aucun aplat, aucune hachure, aucun dégradé, aucune texture, aucune couleur
- projection isométrique : même angle de vue que l'image jointe (vue de trois quarts en plongée, arêtes verticales bien verticales)
- formes simples et lisibles, style cartoon sobre, personnages à grosse tête et petit corps, sans visage détaillé
- rien d'autre dans l'image : pas de sol, pas de cadre, pas de texte, pas de titre
```

Puis la ligne spécifique à la demande :

**Monument** (fiche 007) : « Remplace la boîte grise de l'image par [la cathédrale Saint-Benoît de Castres], dans ce même style, avec exactement la même emprise au sol et le même angle. Simplifie l'architecture : les éléments signatures seulement ([le clocher massif, les contreforts]). »

**Planche de détails** (fiche 009) : « Planche de 9 objets, disposés en grille 3 × 3, largement espacés, chacun isolé sur le blanc, tous à la même échelle (un personnage adulte ferait 1 cm) : [chat assis, poubelle de rue, vélo appuyé, jardinière fleurie, panneau de sens interdit, banc, pigeon, cône de chantier, valise]. »

**Personnage** (fiche 009) : « Planche de 4 poses du même personnage, en ligne, largement espacées : [une vieille dame au béret avec un cabas] — debout de face, marchant vers la gauche, assise, de dos. Même vêtements, même silhouette dans les 4. »

## 3. Planche de test

Avant de lancer les 25 planches : une seule planche de 9 détails, passée dans `pipeline/04_sheets.py`. Si la découpe, la vectorisation et la normalisation du trait sortent 9 SVG propres à la bonne taille, le prompt est validé. Sinon on corrige le prompt (jamais les images) et on refait la planche.

## Règles de génération

- Quatre essais maximum par demande ; on garde le meilleur, on supprime les autres.
- On ne retouche jamais une image ; on reformule le prompt.
- Dépôt des PNG dans `inbox/` avec un nom parlant : `details_rue_01.png`, `perso_vieille_dame.png`, `monument_saint-benoit_v2.png`.
- Le script normalise le trait : quelle que soit l'épaisseur de Gemini, tous les SVG sortent avec la même.
