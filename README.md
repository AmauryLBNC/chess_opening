# Echiquier

Petit projet Python/Pygame autour des echecs. Le dossier contient maintenant une nouvelle entree unifiee, tout en gardant les anciens scripts pour compatibilite.

La nouvelle application regroupe :

- jouer une partie rapide en blitz avec un echiquier cliquable ;
- s'entrainer sur des variantes d'ouverture en rejouant les bons coups cote blanc ;
- s'entrainer sur des variantes d'ouverture cote noir avec orientation adaptee.

L'application utilise des fichiers texte pour stocker les positions et les suites de coups, et des images PNG pour afficher les pieces.

## Lancer le projet

Depuis ce dossier :

```powershell
python main.py
```

## Application web Next.js

Le portage web est dans le meme dossier et ne depend d'aucun backend : les problemes sont exportes dans `data/problems.json`, les images sont servies depuis `public/pieces/`, et Next genere un site statique.

Installation :

```powershell
npm install
```

Relancer la conversion des problemes :

```powershell
python scripts/export_problems.py
```

Developpement local :

```powershell
npm run dev
```

Build statique compatible Vercel :

```powershell
npm run build
```

Deploiement Vercel : pousser le projet sur GitHub puis l'importer dans Vercel. Aucune API route, base de donnees ou configuration serveur n'est necessaire.

### Creer un probleme (web)

L'app web permet de creer un nouveau probleme directement depuis le navigateur, sans backend. Le fichier `.txt` est genere cote client et telecharge par l'utilisateur, qui peut ensuite l'integrer au repo.

Acces : depuis le menu principal, cliquer sur **+ Creer un probleme** (route `/create`).

Flux utilisateur :

1. Choisir le cote (blanc ou noir) : determine le dossier de destination et l'orientation de l'echiquier.
2. Saisir un nom d'ouverture : soit une ouverture existante (autocompletee depuis `data/problems.json`), soit un nouveau nom. Le nom est normalise (minuscules, sans accent, avec underscores).
3. Optionnel : activer le mode **Modifier** pour editer la position de depart. Clic sur une case = cycle vide → pion → cavalier → fou → tour → dame → roi. Toggle separe pour la couleur courante d'edition. Boutons **Standard** et **Vider**.
4. Sortir du mode edition pour figer la position de depart, puis jouer les coups en cliquant piece → case d'arrivee. Le cote a jouer alterne automatiquement.
5. Bouton **Annuler dernier coup** pour revenir en arriere a tout moment.
6. Bouton **Terminer** : ouvre un recap, propose le telechargement du fichier et la copie du contenu.

Pour integrer le fichier genere au repo :

```powershell
# 1. Place le fichier telecharge dans le bon dossier (cote blanc) :
#    problemes/<ouverture>/<numero>.txt
# (cote noir : problemes/black/<ouverture>/<numero>.txt)
# 2. Incremente la premiere ligne de Format.txt dans ce dossier.
# 3. Relance l'export pour mettre a jour data/problems.json :
python scripts/export_problems.py
# 4. Commit et push :
git add problemes data/problems.json
git commit -m "Ajout d'un probleme dans <ouverture>"
git push
```

Vercel redeploiera automatiquement et la nouvelle ligne apparaitra dans le mode entrainement web.

Tests unitaires des helpers web (vitest) :

```powershell
npm install
npm test
```

Anciens lancements encore disponibles :

```powershell
python probleme.pyw
python probleme-black.pyw
python blitz.py
python blitz-black.py
```

Dependances Python utilisees par les scripts :

```powershell
python -m pip install -r requirements.txt
```

`pygame` sert a l'affichage et aux clics, `numpy` sert aux tableaux d'echiquier, `pillow` sert seulement au script de conversion d'icone, et `pyinstaller` sert a generer les executables.

### Installation Windows recommandee

Eviter Python 3.14 pour ce projet pour l'instant : `pygame` peut essayer de se compiler depuis les sources au lieu d'utiliser une roue precompilee, ce qui provoque des erreurs comme `No module named 'distutils.msvccompiler'`.

Utiliser plutot Python 3.13 ou 3.12, puis creer un environnement virtuel dans le projet :

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Si `python --version` affiche encore `Python 3.14.x`, installer Python 3.13 depuis python.org, puis verifier que le terminal utilise bien cette version avant d'installer les dependances.

Diagnostic rapide :

```powershell
python scripts/doctor.py
```

Si un `.venv` a deja ete cree avec Python 3.14, il faut le supprimer avant de recommencer :

```powershell
deactivate
Remove-Item -Recurse -Force .venv
```

Ensuite, apres installation de Python 3.13, relancer :

```powershell
python --version
.\setup.ps1
.\.venv\Scripts\Activate.ps1
python main.py
```

Ne lance `.\.venv\Scripts\Activate.ps1` que si `setup.ps1` termine avec `Installation terminee`. Si `setup.ps1` s'arrete sur Python 3.14, aucun `.venv` compatible n'est cree.

Si Python Manager est installe, `setup.ps1` peut aussi installer Python 3.13 automatiquement et le selectionner pour le projet.

Si `python --version` affiche toujours `3.14`, Windows pointe encore vers l'ancien Python. Dans ce cas, lancer directement Python 3.13 avec son chemin complet, par exemple :

```powershell
& "C:\Users\amaur\AppData\Local\Programs\Python\Python313\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Nouvelle organisation

La refactorisation est progressive : les anciens fichiers ne sont pas supprimes, mais la nouvelle application passe par `main.py` et le package `app/`.

```text
main.py
app/
  ui/
    theme.py
    components.py
    layout.py
    screens.py
  config.py
  assets.py
  models.py
  board.py
  moves.py
  game_state.py
  problem_loader.py
  problem_mode.py
  blitz_mode.py
  renderer_pygame.py
  ui_pygame.py
tests/
  test_core.py
```

| Fichier | Role |
| --- | --- |
| `main.py` | Point d'entree unique. Affiche le menu principal : entrainement blanc, entrainement noir, blitz local, blitz vue noire. |
| `app/config.py` | Constantes globales : tailles, couleurs, chemins, duree du blitz. |
| `app/assets.py` | Chargement robuste des images de pieces depuis `image/`, avec gestion des differences de casse comme `bKN.png` / `bKn.png`. |
| `app/models.py` | Types simples : couleur, orientation, coordonnees, coups, coups appliques. |
| `app/board.py` | Manipulation pure de l'echiquier : lecture/ecriture des cases, application et annulation des coups. |
| `app/moves.py` | Generation des coups, detection d'echec et de mat. |
| `app/game_state.py` | Etat central d'une partie : plateau, joueur courant, historique, coups legaux, annulation. |
| `app/problem_loader.py` | Lecture robuste des fichiers de problemes existants sans changer leur format. |
| `app/problem_mode.py` | Logique du mode entrainement unifie blanc/noir. |
| `app/blitz_mode.py` | Logique du mode blitz dans la nouvelle application. |
| `app/renderer_pygame.py` | Dessin de l'echiquier et des pieces avec orientation blanche ou noire. |
| `app/ui_pygame.py` | Petits composants Pygame : boutons et textes. |
| `app/ui/theme.py` | Mini design system : palette sombre, espacements, rayons, tailles, polices. |
| `app/ui/components.py` | Composants reutilisables : boutons, cartes, panneaux, badges, blocs d'information. |
| `app/ui/layout.py` | Helpers de layout : centrage, grille de cartes, placement echiquier + panneau lateral. |
| `app/ui/screens.py` | Rendu des ecrans UI reutilisables, notamment le menu principal. |
| `tests/test_core.py` | Tests simples sur les modules purs. |
| `tests/test_ui_layout.py` | Tests simples sur le layout UI et les interactions de composants. |

## Fichiers principaux

| Fichier | Role |
| --- | --- |
| `main.py` | Nouvelle entree recommandee pour lancer l'application unifiee. |
| `probleme.pyw` | Application principale pour s'entrainer sur les problemes / variantes cote blanc. Elle lit les dossiers dans `problemes/`, choisit un probleme au hasard, verifie les coups joues et peut afficher la solution. |
| `probleme-black.pyw` | Version equivalente pour les problemes cote noir. Elle lit les variantes dans `problemes/black/`. L'echiquier et les coordonnees sont adaptes au point de vue noir. |
| `blitz.py` | Jeu d'echecs local en blitz 5 minutes. Il gere les clics, les mouvements, les echecs, les mats, le chrono et peut servir a creer des fichiers de problemes. |
| `blitz-black.py` | Variante de `blitz.py` avec l'echiquier oriente pour les noirs. |
| `test.py` | Script utilitaire qui transforme `ajout_probleme_blanc.png` en fichier `.ico` avec Pillow. |
| `probleme.spec` | Configuration PyInstaller pour creer `dist/probleme.exe` a partir de `probleme.pyw`. |
| `info_utile.txt` | Notes rapides avec des commandes PyInstaller. |

## Dossiers

| Dossier | Role |
| --- | --- |
| `image/` | Images PNG des pieces chargees par les scripts Pygame. |
| `echiquier_set_piece/` | Autre jeu d'images de pieces, probablement conserve comme ressource ou sauvegarde. |
| `problemes/` | Base de donnees des problemes cote blanc. Chaque sous-dossier represente une ouverture ou une variante. |
| `problemes/black/` | Base de donnees des problemes cote noir. |
| `sauvegarde/` | Anciennes versions des scripts (`1.0`, `1.1`). A garder comme historique manuel. |
| `build/` | Fichiers temporaires generes par PyInstaller. Peut etre regenere. |
| `dist/` | Executables et ressources exportes par PyInstaller. |
| `probleme-black/` | Dossier de build/export pour la version noire. |
| `probleme-blanc/` | Dossier de build/export pour la version blanche. |
| `.vscode/` | Configuration locale Visual Studio Code. |

## Menu principal

`python main.py` ouvre un menu Pygame avec quatre modes :

| Mode | Role |
| --- | --- |
| `Entrainement blanc` | Charge les variantes dans `problemes/`. |
| `Entrainement noir` | Charge les variantes dans `problemes/black/` et affiche l'echiquier en vue noire. |
| `Blitz local` | Lance une partie blitz 5 minutes avec l'orientation blanche. |
| `Blitz vue noire` | Lance le meme blitz avec l'orientation noire. |

L'interface modernisee utilise :

- fond sombre ;
- cartes de selection au menu principal ;
- panneaux lateraux pour les modes ;
- boutons coherents avec etats hover / disabled ;
- badges de statut ;
- chronos plus lisibles en blitz ;
- indication visuelle de la case selectionnee et des coups proposes quand disponibles.

## Utilisation de `probleme.pyw`

Au demarrage, l'application liste les ouvertures trouvees dans `problemes/`.

1. Cliquer sur une ouverture.
2. Un probleme est choisi au hasard.
3. Jouer le coup attendu en cliquant d'abord sur la piece, puis sur la case d'arrivee.
4. Si le coup est correct, l'application joue automatiquement la reponse suivante de la variante.
5. Quand toute la variante est terminee, le message `GOOD` s'affiche.

Boutons disponibles :

| Bouton | Role |
| --- | --- |
| `nouveau probleme` | Charge un autre probleme au hasard dans la meme ouverture. |
| `precedent` | Annule le dernier coup enregistre. |
| `solution` | Joue automatiquement les prochains coups de la variante. |
| `variante` | Revient au choix des ouvertures. |
| `refaire` | Recommence le meme probleme depuis le debut. |

## Utilisation de `probleme-black.pyw`

Le fonctionnement est le meme que `probleme.pyw`, mais les fichiers sont lus dans :

```text
problemes/black/<nom_de_variante>/
```

Cette version convertit les coordonnees pour afficher et jouer depuis le point de vue noir.

## Utilisation de `blitz.py`

`blitz.py` ouvre un echiquier avec deux joueurs en local et un chrono de 5 minutes par joueur.

Fonctions principales :

- selection d'une piece par clic ;
- calcul des coups possibles ;
- deplacement sur la case d'arrivee ;
- gestion des prises, roques, promotions et prises en passant ;
- verification de l'echec et du mat ;
- bouton `precedent` pour annuler un coup ;
- bouton `nouvelle partie`, utilise aussi dans le code pour creer un fichier de probleme.

Attention : dans le code actuel, la creation de fichiers pointe vers `problemes/defense_francaise/`. Pour ajouter une autre ouverture avec `blitz.py`, il faut modifier le chemin dans `creation_fichier()` et `correspondance_coup()`.

Dans la nouvelle application, le mode blitz est dans `app/blitz_mode.py` et utilise `app/game_state.py`, `app/board.py` et `app/moves.py`.

## Format des problemes

Chaque ouverture est un dossier, par exemple :

```text
problemes/sicilienne/
```

Ce dossier contient :

```text
Format.txt
1.txt
2.txt
3.txt
...
```

`Format.txt` commence par le nombre de problemes disponibles dans le dossier. Exemple :

```text
9
```

Un fichier de probleme contient :

1. les 8 lignes de l'echiquier de depart ;
2. puis la liste des coups attendus, un coup par ligne.

Exemple simplifie :

```text
51 0 31 91 81 31 41 51
11 11 0 11 11 11 11 11
0 0 41 0 0 0 0 0
0 0 11 0 0 0 0 0
0 0 0 0 12 0 0 0
0 0 0 0 0 42 0 0
12 12 12 12 0 12 12 12
52 42 32 92 82 32 0 52
f 1 b 5 32 0
a 7 a 6 11 0
```

Une ligne de coup suit ce format :

```text
colonne_depart ligne_depart colonne_arrivee ligne_arrivee piece_depart piece_arrivee
```

Exemple :

```text
f 1 b 5 32 0
```

Cela signifie : la piece `32` part de `f1`, arrive en `b5`, et la case d'arrivee etait vide (`0`).

## Codes des pieces

Le plateau est un tableau 8 x 8 de nombres. `0` signifie case vide.

| Code | Piece |
| --- | --- |
| `11` | pion noir |
| `12` | pion blanc |
| `31` | fou noir |
| `32` | fou blanc |
| `41` | cavalier noir |
| `42` | cavalier blanc |
| `51` | tour noire |
| `52` | tour blanche |
| `81` | roi noir |
| `82` | roi blanc |
| `91` | dame noire |
| `92` | dame blanche |

Logique generale :

- le premier chiffre indique le type de piece ;
- le deuxieme chiffre indique la couleur ;
- impair = noir ;
- pair = blanc.

## Fonctions importantes dans le code

| Fonction | Role |
| --- | --- |
| `recup_donnee()` | Lit un fichier de probleme, charge le tableau de depart et convertit les coups texte en coordonnees utilisables par le programme. |
| `echiquier()` | Dessine les cases de l'echiquier. |
| `actualiser_echequier()` | Redessine toutes les pieces sur le plateau. |
| `gestioncoordonne()` | Convertit la position de la souris en coordonnees de case. |
| `detectionPiece()` | Affiche la bonne image selon le code de la piece presente sur une case. |
| `mouvementpion()` | Applique le deplacement d'une piece sur le tableau, avec les cas speciaux comme promotion, roque et prise en passant. |
| `detectionmouvementgen()` | Dans les scripts blitz, calcule les coups possibles pour une piece. |
| `CheckEchec()` | Verifie si un roi est en echec. |
| `checkmate()` | Verifie si la position est mat. |
| `correspondance_coup()` | Affiche ou ecrit un coup au format texte utilise par les problemes. |
| `creation_fichier()` | Cree un nouveau fichier de probleme a partir de la position courante. |
| `affichage_final()` | Affiche l'ecran de fin. |
| `draw_rounded_rect()` | Dessine les boutons arrondis dans les menus de problemes. |

## Generer un executable

Commande notee dans le projet :

```powershell
pyinstaller --onefile --windowed probleme.pyw
```

Ou avec le fichier spec :

```powershell
pyinstaller probleme.spec
```

Pour la version noire :

```powershell
pyinstaller probleme-black\probleme-black.spec
```

Important : les scripts chargent les images et problemes avec des chemins relatifs comme `image/...` et `problemes/...`. Si l'executable ne trouve pas les pieces ou les variantes, copier les dossiers `image/` et `problemes/` a cote de l'executable, ou les ajouter explicitement dans la section `datas` du fichier `.spec`.

## Tests

Les tests actuels verifient les fonctions pures principales : coordonnees, plateau, annulation, chargement des problemes blanc/noir, et quelques garanties de layout UI.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
```

Verification de syntaxe :

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q app main.py tests scripts
```

## Notes importantes

- Le projet depend du dossier courant : il faut lancer les scripts depuis la racine du projet pour que les chemins relatifs fonctionnent.
- Sur Windows, les noms de fichiers ne sont pas sensibles a la casse. Sur Linux ou macOS, verifier les noms `bKN.png` / `wKN.png`, car certains scripts demandent `bKn.png` / `wKn.png`.
- Les dossiers `build/` et `dist/` sont des sorties de compilation. Le code source principal est dans les fichiers `.py` et `.pyw` a la racine.
- La nouvelle refactorisation ne change pas le format des fichiers dans `problemes/`.
- Les anciens scripts restent disponibles tant que la nouvelle application n'a pas remplace toutes les habitudes d'utilisation.
