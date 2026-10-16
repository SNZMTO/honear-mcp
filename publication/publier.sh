#!/bin/sh
# Publie un commit du dépôt privé (SNZMTO/honear-mcp-atelier) dans le dépôt public (SNZMTO/honear-mcp), d'un seul commit :
# l'arbre de ce commit tel quel, sans son historique. Avant, il vérifie que ce commit est poussé et que sa CI est verte, puis
# qu'aucun secret ne part : ni jeton, ni clé, ni l'adresse IP du VPS (qu'il lit dans ~/vps/LISEZMOI.md, sans jamais l'écrire
# ni l'afficher), ni une adresse e-mail qu'on ne connaît pas. Sans --envoyer, il ne fait que vérifier.
#
#   sh publication/publier.sh [commit] [--envoyer]
#   sh publication/publier.sh --verifier <dossier>       (les mêmes vérifications, sur un dossier quelconque)
set -eu
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC=SNZMTO/honear-mcp
PRIVE=SNZMTO/honear-mcp-atelier
git() { command git -C "$RACINE" "$@"; }

# Ce qui ne part jamais : un jeton GitHub, une clé privée, une clé des statistiques écrite en clair, une clé AWS ou Slack.
SECRETS='gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|STATISTIQUES_CLE=[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]+'
# Les seules adresses e-mail qu'un fichier peut porter.
ADRESSES_CONNUES='users\.noreply\.github\.com|noreply@anthropic\.com|contact@mateosan\.fr|bonjour@honear\.fr'

verifier() {
  dossier="$1"
  echec=0
  for ip in $(grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "$HOME/vps/LISEZMOI.md" 2>/dev/null | grep -v '^127\.' | sort -u); do
    if grep -rlF -- "$ip" "$dossier" >/dev/null 2>&1; then
      echo "L'adresse IP du VPS est dans : $(grep -rlF -- "$ip" "$dossier" | sed "s#^$dossier/##" | tr '\n' ' ')"
      echec=1
    fi
  done
  # Les fausses clés des tests s'appellent « faussecle-… » : elles peuvent partir.
  secrets="$(grep -rnoE -- "$SECRETS" "$dossier" | grep -v 'STATISTIQUES_CLE=faussecle-' | cut -d: -f1 | sort -u || true)"
  if [ -n "$secrets" ]; then
    echo "Un secret est dans : $(echo "$secrets" | sed "s#^$dossier/##" | tr '\n' ' ')"
    echec=1
  fi
  inconnues="$(grep -rhoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' "$dossier" | grep -vE "$ADRESSES_CONNUES" | grep -vE '@[0-9]|\.(py|ts|js|json|woff2|webp)$' | sort -u || true)"
  if [ -n "$inconnues" ]; then
    echo "Des adresses e-mail inconnues : $(echo "$inconnues" | tr '\n' ' ')"
    echec=1
  fi
  for fichier in .env statistiques.env; do
    [ -z "$(find "$dossier" -name "$fichier" -print -quit)" ] || { echo "Un fichier $fichier part."; echec=1; }
  done
  return "$echec"
}

if [ "${1:-}" = --verifier ]; then
  verifier "${2:?Quel dossier ?}" && echo "Rien qui ne doive partir."
  exit
fi

ENVOYER=0
QUEL=HEAD
for argument in "$@"; do
  if [ "$argument" = --envoyer ]; then ENVOYER=1; else QUEL="$argument"; fi
done
COMMIT="$(git rev-parse --verify --quiet "$QUEL^{commit}")" || { echo "« $QUEL » n'est pas un commit."; exit 1; }
COURT="$(git rev-parse --short=7 "$COMMIT")"

git merge-base --is-ancestor "$COMMIT" origin/main || { echo "Le commit $COURT n'est pas sur origin/main : pousse-le d'abord."; exit 1; }
CI="$(gh api "repos/$PRIVE/actions/runs?head_sha=$COMMIT" --jq '[.workflow_runs[] | .conclusion] | if length == 0 then "absente" elif all(. == "success") then "verte" else "pas verte" end')"
[ "$CI" = verte ] || { echo "La CI du commit $COURT est $CI."; exit 1; }

TRAVAIL="$(mktemp -d)"
trap 'rm -rf "${TRAVAIL:?}"' EXIT
mkdir "$TRAVAIL/arbre"
git archive "$COMMIT" | tar -x -C "$TRAVAIL/arbre"
verifier "$TRAVAIL/arbre" || { echo "Rien n'est publié."; exit 1; }
echo "Le commit $COURT peut partir : rien qui ne doive partir."
[ "$ENVOYER" = 1 ] || { echo "(Sans --envoyer, rien n'est publié.)"; exit 0; }

gh repo clone "$PUBLIC" "$TRAVAIL/public" -- --quiet
find "$TRAVAIL/public" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a "$TRAVAIL/arbre/." "$TRAVAIL/public/"
command git -C "$TRAVAIL/public" add -A
command git -C "$TRAVAIL/public" -c user.name="Mateo Sanchez" -c user.email="221996800+SNZMTO@users.noreply.github.com" commit -q -F - <<MESSAGE
Le MCP de Honear, tel qu'au commit $COURT de son atelier, le $(date -u +%d/%m/%Y)

Publié d'un bloc depuis le dépôt privé où le travail se fait (voir « L'historique », dans le README).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MESSAGE
command git -C "$TRAVAIL/public" push -q origin HEAD:main
echo "Publié : https://github.com/$PUBLIC"
