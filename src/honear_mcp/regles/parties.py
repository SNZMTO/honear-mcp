"""La saisie libre de Honear, partie par partie : le portage de `jugerLesParties` et de `ciblesDe` (`src/regles/modes/libre.ts`).

Une saisie se lit entière, en morceaux de part et d'autre d'un « feat », mot à mot, et peut trouver plusieurs parties d'un
coup, dans l'ordre qu'on veut. Le vrai nom d'une partie vient en premier parmi ce qu'elle accepte, ses surnoms ensuite.
"""

import re
from collections.abc import Sequence
from typing import Literal

from honear_mcp.regles.jugement import Verdict, juger, normaliser
from honear_mcp.ressources.honear import JUGEMENT

type Partie = Literal["artiste", "titre", "feat"]

_LIAISON = re.compile(rf"\b(?:{'|'.join(JUGEMENT.liaisons)})\b\.?", re.IGNORECASE | re.ASCII)
_BLANC = r"[\s\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]"
_ENTRE_DEUX_INVITES = re.compile(rf"{_BLANC}*(?:,|&|\+|/|\bet\b|\band\b|\bx\b){_BLANC}*", re.IGNORECASE | re.ASCII)
_DU_PIRE_AU_MEILLEUR: tuple[Verdict, ...] = ("faux", "presque", "juste")


def les_invites(feat: str) -> list[str]:
    """Les invités d'un feat, un par un : « Alonzo, Gradur, KeBlack & Awa Imani » ; le feat tel quel s'il n'en nomme qu'un."""
    return [n.strip() for n in _ENTRE_DEUX_INVITES.split(feat) if n.strip()]


def cibles_de(artiste: str, titre: str, feat: str | None, surnoms: dict[Partie, list[str]]) -> dict[Partie, list[str]]:
    """Ce que chaque partie accepte : son vrai nom d'abord, ses surnoms ensuite ; un feat entier, ou l'un de ses invités."""
    return {
        "artiste": [artiste, *surnoms.get("artiste", [])],
        "titre": [titre, *surnoms.get("titre", [])],
        "feat": [feat, *[n for n in les_invites(feat) if n != feat]] if feat is not None else [],
    }


def _enchainements(parties: Sequence[Partie]) -> list[list[Partie]]:
    """Toutes les façons d'enchaîner des parties : chacune seule, puis deux, puis trois, dans tous les ordres."""
    suites: list[list[Partie]] = []
    for rang, partie in enumerate(parties):
        reste = [p for j, p in enumerate(parties) if j != rang]
        suites += [[partie], *[[partie, *suite] for suite in _enchainements(reste)]]
    return suites


def _suites_de_mots(texte: str) -> list[str]:
    """Chaque suite de mots qui se suivent : « Kofs Jul » donne « kofs », « kofs jul » et « jul » ; un morceau trop court ne
    compte que s'il est toute la saisie."""
    mots = [m for m in normaliser(texte, articles=False).split(" ") if m]
    return [
        " ".join(mots[debut:fin])
        for debut in range(len(mots))
        for fin in range(debut + 1, len(mots) + 1)
        if len("".join(mots[debut:fin])) >= JUGEMENT.morceau_au_moins or (debut == 0 and fin == len(mots))
    ]


def juger_les_parties(
    texte: str, parties: Sequence[Partie], cibles: dict[Partie, list[str]], deja_trouve: Sequence[Partie]
) -> tuple[list[Partie], Verdict]:
    """Ce qu'une saisie trouve parmi les parties qui restent, et son verdict."""
    morceaux = [m for m in [texte, *_LIAISON.split(texte)] if m.strip()]

    def meilleur(partie: Partie) -> Verdict:
        verdicts = [juger(m, c) for m in morceaux for c in cibles[partie]]
        return max(verdicts, key=_DU_PIRE_AU_MEILLEUR.index, default="faux")

    lectures = [texte, _LIAISON.sub(" ", texte)]
    en_un_coup = {
        p
        for suite in _enchainements(parties)
        if len(suite) > 1 and any(juger(lecture, " ".join(cibles[q][0] for q in suite)) == "juste" for lecture in lectures)
        for p in suite
    }
    suites = [s for m in morceaux for s in _suites_de_mots(m)]
    trouve = [
        p
        for p in parties
        if p not in deja_trouve
        and (p in en_un_coup or meilleur(p) == "juste" or any(juger(s, c) == "juste" for s in suites for c in cibles[p]))
    ]
    if trouve:
        return trouve, "juste"
    presque = any(p not in deja_trouve and meilleur(p) == "presque" for p in parties)
    return [], "presque" if presque else "faux"
