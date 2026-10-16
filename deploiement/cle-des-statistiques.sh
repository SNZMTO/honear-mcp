#!/bin/sh
# Donne à l'assistant d'exploitation la clé des statistiques de Honear : copiée de /etc/honear/statistiques.env (que seul root
# lit) dans ~/.config/honear-mcp/statistiques.env de qui lance le script (0600, à lui seul). Elle ne s'affiche jamais. À lancer
# par Mateo, dans un vrai terminal, une fois (et de nouveau si la clé change).
#
#   sudo sh deploiement/cle-des-statistiques.sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Lance-le avec sudo."; exit 1; }
QUI="${SUDO_USER:-}"
[ -n "$QUI" ] && [ "$QUI" != root ] || { echo "Lance-le avec sudo, depuis ton compte : la clé ira chez toi."; exit 1; }
SOURCE=/etc/honear/statistiques.env
[ -r "$SOURCE" ] || { echo "$SOURCE n'existe pas : la mise en ligne de Honear la crée."; exit 1; }
MAISON="$(getent passwd "$QUI" | cut -d: -f6)"
GROUPE="$(id -gn "$QUI")"
DOSSIER="$MAISON/.config/honear-mcp"
install -d -m 0700 -o "$QUI" -g "$GROUPE" "$DOSSIER"
(umask 077 && grep '^STATISTIQUES_CLE=' "$SOURCE" > "$DOSSIER/statistiques.env")
chown "$QUI:$GROUPE" "$DOSSIER/statistiques.env"
chmod 0600 "$DOSSIER/statistiques.env"
echo "La clé est copiée pour $QUI, dans $DOSSIER/statistiques.env (sans l'afficher)."
