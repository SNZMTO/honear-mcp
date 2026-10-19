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
CLE="$DOSSIER/statistiques.env"
# root n'écrit pas à travers un lien posé chez quelqu'un : ni ~/.config, ni le dossier, ni la clé ne peuvent en être un.
for chemin in "$MAISON/.config" "$DOSSIER" "$CLE"; do
  [ ! -L "$chemin" ] || { echo "$chemin est un lien symbolique : rien n'est copié."; exit 1; }
done
install -d -m 0700 -o "$QUI" -g "$GROUPE" "$DOSSIER"
# La clé s'écrit d'abord dans un fichier à root seul, puis install la pose à sa place, au nom de $QUI : il remplace la cible au
# lieu de l'ouvrir, et ne suit donc pas un lien posé entre-temps.
PROVISOIRE="$(mktemp)"
trap 'rm -f "$PROVISOIRE"' EXIT
grep '^STATISTIQUES_CLE=' "$SOURCE" > "$PROVISOIRE"
install -m 0600 -o "$QUI" -g "$GROUPE" "$PROVISOIRE" "$CLE"
echo "La clé est copiée pour $QUI, dans $CLE (sans l'afficher)."
