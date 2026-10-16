# Mettre le MCP de Honear en ligne

Le MCP tourne sur le VPS de Honear, dans un conteneur Docker construit depuis ce dépôt, derrière le frontal du VPS (Caddy, dépôt
`vps`, `~/vps`), qui tient le HTTPS de mcp.honear.fr.

```
assistant (claude.ai, Claude Code…) ──HTTPS──▶ frontal (Caddy) ──réseau « honear-mcp »──▶ honear-mcp:8790 (/mcp, /, /sante)
                                                                                           └──▶ /var/lib/honear-mcp/listes
Honear (le jeu) ──réseau interne « honear-listes »──▶ honear-mcp:8791 (/listes/<id>)
```

| Fichier | Rôle |
| --- | --- |
| `Dockerfile` | L'image : le serveur et ses dépendances, installés par uv d'après `uv.lock`, puis Python seul, sans droits. Images figées à leur empreinte. |
| `deploiement/compose.yaml` | Le conteneur : aucun port ouvert, aucune capacité, lecture seule, mémoire et processus comptés, deux réseaux. |
| `deploiement/mettre-en-ligne.sh` | À chaque version : construit l'image au commit courant, relance le MCP, vérifie qu'il répond. |
| `deploiement/cle-des-statistiques.sh` | La clé des statistiques de Honear, copiée pour l'assistant d'exploitation (Mateo la lance). |

Le frontal (`~/vps/frontal`) a le bloc de mcp.honear.fr dans son Caddyfile, et rejoint le réseau `honear-mcp` : il ne passe que
le port 8790, et ne compresse pas les réponses en flux de `/mcp`.

Le serveur croit l'adresse que le frontal lui donne (`X-Forwarded-For`, `forwarded_allow_ips="*"`) : c'est sûr parce qu'aucun
port n'est publié et que seul le frontal joint le 8790. Publier ce port laisserait n'importe qui se faire passer pour une autre
adresse, et contourner la limite par adresse.

## Mettre en ligne

Depuis ce dossier de travail, jamais dans `/srv/honear-mcp` (c'est le script qui le remplit) ; quand Mateo dit « deploy », et
quand personne ne joue (une construction occupe la machine du jeu).

```
uv run ruff check && uv run mypy && uv run pytest && git commit … && sudo sh deploiement/mettre-en-ligne.sh
```

L'ordre compte quand un réseau naît : Honear crée `honear-listes`, le MCP crée `honear-mcp`, et le frontal rejoint ce dernier.
Le MCP est en ligne depuis le 16 octobre 2026.

- **Vérifier :** `curl -s https://mcp.honear.fr/sante` rend `{"deezer_en_attente": …, "recherches_gardees": …, "listes": …}`.
- **Les journaux :** `sudo docker compose --project-directory /srv/honear-mcp logs --tail 100` (ni adresse IP ni recherche n'y
  sont écrites).
- **Revenir en arrière** sans reconstruire : changer `VERSION` dans `/srv/honear-mcp/.env` pour une des trois images gardées
  (`sudo docker image ls honear-mcp`), puis `sudo docker compose --project-directory /srv/honear-mcp up -d`.
