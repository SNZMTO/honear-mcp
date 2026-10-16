"""Le texte qu'un modèle écrit et qu'un écran montrera : nettoyé avant d'être gardé.

Un nom de liste, un surnom ou une anecdote finissent sur l'écran de l'hôte d'une partie, chez quelqu'un. On les met sous une
seule forme Unicode, on ôte ce qui ne se voit pas mais agit (les caractères de contrôle, ceux qui retournent le sens de
l'écriture), les liens, et les blancs en trop.
"""

import re
import unicodedata

_LIEN = re.compile(r"(?:https?://|www\.)\S*", re.IGNORECASE)
_BLANCS = re.compile(r"\s+")


def _visible(signe: str) -> bool:
    """Vrai pour un signe qui s'affiche : ni contrôle (Cc), ni format invisible (Cf, dont les marques de sens d'écriture)."""
    return unicodedata.category(signe) not in {"Cc", "Cf"} or signe in "\t\n"


def nettoyer(texte: str) -> str:
    """Le texte sous sa forme composée (NFC), sans signe invisible qui agit, sans lien, sur une seule ligne."""
    compose = unicodedata.normalize("NFC", texte)
    visible = "".join(s for s in compose if _visible(s))
    return _BLANCS.sub(" ", _LIEN.sub("", visible)).strip()
