#!/bin/sh
# Met le MCP de Honear en ligne sur le VPS, depuis ce dépôt : construit l'image, étiquetée à son commit, pose compose.yaml dans
# /srv/honear-mcp et relance le MCP, puis vérifie qu'il répond par le frontal. Ce qui est en ligne est toujours un commit : il
# refuse un dépôt qui a des changements. Une recherche en cours s'arrête (les listes restent) : il refuse tant que le MCP attend
# Deezer, sauf avec --maintenant. La première fois, il crée l'utilisateur honear-mcp et le dossier des listes. Le jeu doit être en
# ligne avant lui (il crée le réseau « honear-listes »), et le frontal après (dépôt « vps », son bloc mcp.honear.fr).
#
#   sudo sh deploiement/mettre-en-ligne.sh [--maintenant]
#
# Avec sudo, depuis le compte à qui est la copie : il refuse root lui-même, car git la lit au nom de ce compte.
#
# Revenir à la version d'avant sans reconstruire : changer VERSION dans /srv/honear-mcp/.env (les trois dernières images sont
# gardées : sudo docker image ls honear-mcp), puis sudo docker compose --project-directory /srv/honear-mcp up -d
set -eu
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
CIBLE=/srv/honear-mcp
DOMAINE=mcp.honear.fr
[ "$(id -u)" = 0 ] || { echo "Lance-le avec sudo."; exit 1; }
QUI="${SUDO_USER:-}"
[ -n "$QUI" ] && [ "$QUI" != root ] || { echo "Lance-le avec sudo, depuis ton compte : git lit la copie à ton nom."; exit 1; }
command -v docker >/dev/null || { echo "Docker n'est pas là : prépare d'abord le VPS (dépôt « vps », sudo sh preparer.sh)."; exit 1; }
# git lit la copie au nom de qui l'a lancé, jamais en root : un réglage de la copie qui lance une commande (core.fsmonitor…)
# ne tourne qu'avec ses droits à lui (la classe de CVE-2022-24765).
git() { sudo -H -u "$QUI" git -C "$RACINE" "$@"; }

if [ -n "$(git status --porcelain)" ]; then
  echo "Le dépôt a des changements qui ne sont pas commités : commite-les d'abord."
  git status --short
  exit 1
fi
VERSION="$(git rev-parse --short=12 HEAD)"

docker network inspect honear-listes >/dev/null 2>&1 ||
  { echo "Le réseau honear-listes n'existe pas : mets d'abord en ligne une version de Honear qui le crée."; exit 1; }

if [ "${1:-}" != --maintenant ]; then
  ATTENTE="$(curl -fsS --max-time 5 "https://$DOMAINE/sante" 2>/dev/null | sed -n 's/.*"deezer_en_attente":\([0-9]*\).*/\1/p')"
  if [ -n "$ATTENTE" ] && [ "$ATTENTE" != 0 ]; then
    echo "$ATTENTE recherche(s) en cours chez Deezer : réessaie dans un instant (ou avec --maintenant)."
    exit 1
  fi
fi

# L'utilisateur à qui appartiennent les listes, sans shell ni droits, et leur dossier, que lui seul lit.
id honear-mcp >/dev/null 2>&1 || useradd --system --user-group --no-create-home --shell /usr/sbin/nologin honear-mcp
install -d -m 0755 /var/lib/honear-mcp
install -d -m 0700 -o honear-mcp -g honear-mcp /var/lib/honear-mcp/listes

printf '== L’image du MCP, version %s\n' "$VERSION"
docker build -t "honear-mcp:$VERSION" "$RACINE"

printf '== Le conteneur\n'
install -d -m 0755 "$CIBLE"
install -m 0644 "$RACINE/deploiement/compose.yaml" "$CIBLE/"
printf 'VERSION=%s\nUID_DU_MCP=%s\nGID_DU_MCP=%s\n' "$VERSION" "$(id -u honear-mcp)" "$(id -g honear-mcp)" > "$CIBLE/.env"
docker compose --project-directory "$CIBLE" up -d --wait --remove-orphans

printf '== Le ménage : les trois dernières images restent, de quoi revenir en arrière\n'
docker image ls honear-mcp --format '{{.Repository}}:{{.Tag}}' | tail -n +4 | xargs -r docker image rm || true
docker builder prune -f --filter until=168h >/dev/null

printf '== Vérifications\n'
SANTE=''
for _ in 1 2 3 4 5 6; do
  if SANTE="$(curl -fsS --max-time 5 "https://$DOMAINE/sante" 2>/dev/null)"; then break; fi
  SANTE=''
  sleep 5
done
if [ -n "$SANTE" ]; then
  printf 'En ligne : https://%s/mcp (version %s)\n%s\n' "$DOMAINE" "$VERSION" "$SANTE"
else
  echo "Le MCP tourne, mais https://$DOMAINE ne répond pas : le frontal a-t-il son bloc ? (dépôt « vps », sudo sh frontal/mettre-en-ligne.sh)"
  echo "Ce que dit le MCP : sudo docker compose --project-directory $CIBLE logs --tail 50"
  exit 1
fi
