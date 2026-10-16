# Le MCP de Honear, pour Claude

Un serveur MCP en Python pour Honear (https://honear.fr), le blind test entre potes. Le modèle du client choisit les titres
d'une playlist sur mesure ; le serveur les retrouve chez Deezer, les vérifie, et les enregistre pour que le jeu les joue. Il
sera en ligne sur **https://mcp.honear.fr**. On écrit en français : le code, les documents, les commits.

## Où lire

- `LISEZMOI.md` : les couches, les modules, ce qui a été tranché, ce qui attend.
- `NOTES-TECHNIQUES.md` : Deezer (le budget partagé avec Honear, la recherche, les drapeaux), les listes (ce que Honear lit,
  le rangement, le départage), le protocole, `/sante`, les journaux.
- `RGPD.md` : ce que le serveur reçoit, ce qu'il garde, et pour combien de temps.
- Le cahier de lancement : `~/honear-mcp-prompt.md` (les phases, les décisions, les règles de travail).

## Commandes

```
uv sync --frozen        # l'outillage et les dépendances, d'après uv.lock
uv run ruff check       # le lint
uv run ruff format      # le format
uv run mypy             # les types, en strict
uv run pytest           # les tests, dont les règles du code (tests/test_sources.py)
HONEAR_MCP_LISTES=/tmp/listes uv run honear-mcp   # le serveur, sur http://127.0.0.1:8790/mcp (et :8791 pour Honear)
uv run honear-exploitation                         # l'assistant d'exploitation, en stdio
npm ci --prefix interface && npm run --prefix interface construire   # le script de la fenêtre du mini blind test
```

## Les règles du code

`tests/test_sources.py` les vérifie : un test rouge là, c'est une règle enfreinte, pas un test à changer.

- Les couches ne lisent que celles du dessous : `ressources` ← `regles` ← `sources` ← `reseau` ← `outils` ← `serveurs`.
- Un réglage (une durée, une borne, un quota) se lit dans `ressources/reglages.py` ; un texte montré aux gens ou à leur
  modèle, dans `ressources/textes.py`. Ceux de l'assistant d'exploitation sont à part (`…_d_exploitation.py`) : le serveur
  public n'en lit rien. Les ressources sont des données, jamais du code.
- L'heure et l'attente ne se lisent que dans `reseau/horloge.py`. Rien ne tire au sort.
- Ni `Any`, ni `cast`, ni vérification coupée, ni `print`. Chaque module commence par une docstring, et tient en 200 lignes.
- Les tests passent par un vrai client MCP (en mémoire) contre le faux Deezer (`tests/faux_deezer.py`) : jamais le vrai réseau.
- `ressources/honear.py` et `tests/jugement-de-honear.json` sont écrits par Honear (`npm run exporter-pour-le-mcp -- ~/honear-mcp`,
  dans `~/miel-dev`) : on ne les retouche jamais à la main.
- Remplacer, c'est supprimer le jour même : pas de code mort, rien de provisoire, pas de fonction écrite pour les tests.

## Mettre en ligne

`HEBERGEMENT.md` : `sudo sh deploiement/mettre-en-ligne.sh`, seulement quand Mateo dit « deploy », et quand personne ne joue à
Honear (la construction occupe la machine du jeu). Le bloc de mcp.honear.fr vit dans le frontal (`~/vps/frontal/Caddyfile`) ;
dans `~/vps`, on ne commite que ses propres fichiers.

## L'assistant d'exploitation

Pour Mateo seul, en stdio : `claude mcp add honear-exploitation -- uv run --directory ~/honear-mcp honear-exploitation`. Il lit,
et ne fait rien d'autre. Sa clé, `~/.config/honear-mcp/statistiques.env`, ne se lit pas à voix haute, ne se copie pas.

## Ce à quoi on ne touche jamais

- `/etc/honear/courrier.env`, `/var/lib/honear/` (les comptes des joueurs de Honear), la branche locale `avant-reecriture`
  de Honear.
- Aucun secret sur GitHub, et jamais l'adresse IP du VPS dans un dépôt public.

## Les dépôts

Ce dossier est le dépôt privé `SNZMTO/honear-mcp-atelier`, avec un historique normal. Le dépôt public `SNZMTO/honear-mcp`
recevra le projet d'un bloc à chaque publication. Créer un dépôt ou pousser vers le public : demander à Mateo d'abord.

## Comment Mateo veut qu'on travaille

Une phase par tour, 4 heures au plus ; une seule passe de vérification (lint, types, tests, un essai dans un vrai client) ;
pas de sous-agents ni de mesures de performance ; un outil qui refuse, on s'arrête et on le dit. Le compte rendu est court :
ce qui est fait, ce qui a été tranché, ce qui reste.
