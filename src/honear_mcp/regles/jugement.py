"""Le jugement d'une réponse tapée, comparée à ce qu'on attend : le portage de celui de Honear (`src/regles/jugement.ts`).

Il tolère les accents, les majuscules, la ponctuation, les « feat. » et ce qui les suit, les parenthèses, les petits mots du
début, des fautes de frappe, et ce qui s'écrit autrement mais se dit pareil. Une seule vérité : ses réglages viennent de Honear
(`ressources/honear.py`, que Honear écrit), et `tests/test_jugement.py` le juge contre une table que Honear a jugée lui-même.
Les expressions sont celles du jeu, en ASCII comme en JavaScript : après la normalisation, il ne reste que a à z et 0 à 9.

Un texte ne se normalise qu'une fois : les caches gardent en mémoire les derniers textes jugés (`TEXTES_JUGES_EN_MEMOIRE` au
plus chacun), ce qu'on tape compris, jusqu'à ce que d'autres les chassent ou que le serveur redémarre (`RGPD.md` le dit).
"""

import re
import unicodedata
from functools import lru_cache
from typing import Literal

from honear_mcp.ressources.honear import JUGEMENT
from honear_mcp.ressources.reglages import TEXTES_JUGES_EN_MEMOIRE

type Verdict = Literal["juste", "presque", "faux"]

_LIGATURES = {"œ": "oe", "æ": "ae", "ß": "ss"}
_DIACRITIQUES = re.compile(r"[\u0300-\u036f]")
_PARENTHESES = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_FEAT = re.compile(r"\b(feat|ft|featuring)\b.*$", re.ASCII)
_AUTRE_QUE_LETTRES = re.compile(r"[^a-z0-9]+")


@lru_cache(maxsize=TEXTES_JUGES_EN_MEMOIRE)
def normaliser(texte: str, *, articles: bool = True) -> str:
    """Ce qui reste d'une saisie quand on ne garde que ce qui compte : des lettres et des chiffres sans accents, des mots séparés
    d'une espace ; sans les petits mots du début (« Démons de minuit » pour « Les Démons de minuit »), sauf si `articles` est
    faux."""
    minuscules = "".join(_LIGATURES.get(c, c) for c in texte.lower())
    sans_accents = _DIACRITIQUES.sub("", unicodedata.normalize("NFD", minuscules))
    nu = _FEAT.sub(" ", _PARENTHESES.sub(" ", sans_accents), count=1).replace("&", " et ")
    mots = [m for m in _AUTRE_QUE_LETTRES.sub(" ", nu).strip().split(" ") if m]
    while articles and len(mots) > 1 and mots[0] in JUGEMENT.articles:
        mots.pop(0)
    return " ".join(mots)


def fautes(a: str, b: str) -> int:
    """Le nombre de fautes de frappe d'un mot à l'autre : une lettre en trop, en moins, changée, ou deux voisines inversées."""
    d = [[i if j == 0 else j if i == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cout = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cout)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


_A_L_OREILLE = [
    (re.compile("ph"), "f"),
    (re.compile("s?ch|sh"), "§"),
    (re.compile("([tg])h"), r"\1"),
    (re.compile("ck|qu|q"), "k"),
    (re.compile("c(?=[eiy])"), "s"),
    (re.compile("c"), "k"),
    (re.compile("gu(?=[eiy])"), "g"),
    (re.compile("g(?=[eiy])"), "j"),
    (re.compile("y"), "i"),
    (re.compile("z"), "s"),
    (re.compile("w"), "u"),
    (re.compile("eau|au"), "o"),
    (re.compile("ou|oo"), "u"),
    (re.compile("ai|ei"), "e"),
    (re.compile("ee|ea"), "i"),
    (re.compile("h"), ""),
    (re.compile(r"(.)\1+"), r"\1"),
]
_FIN_MUETTE = re.compile(r"(..)[esx]$")


@lru_cache(maxsize=TEXTES_JUGES_EN_MEMOIRE)
def a_l_oreille(texte: str) -> str:
    """Ce qu'on entend d'un texte déjà normalisé : les lettres qui se disent pareil ramenées à une seule (ph et f, c dur et k…),
    le h muet ôté, les lettres doublées simplifiées, le e, le s et le x muets de la fin d'un mot oubliés."""
    mots = []
    for mot in texte.split(" "):
        entendu = mot
        for motif, par in _A_L_OREILLE:
            entendu = motif.sub(par, entendu)
        mots.append(_FIN_MUETTE.sub(r"\1", entendu, count=1))
    return " ".join(mots)


def _fautes_au_plus(a: str, b: str, au_plus: float) -> float:
    """Les fautes, quand elles peuvent compter : deux longueurs trop éloignées le disent d'avance, sans rien compter (le portage
    de `fautesAuPlus`). Une faute change la longueur d'une lettre au plus : au-delà de `au_plus`, aucun verdict ne change."""
    return au_plus + 1 if abs(len(a) - len(b)) > au_plus else fautes(a, b)


def juger(saisie: str, attendu: str) -> Verdict:
    """Une saisie comparée à ce qu'on attend : juste, presque, ou faux."""
    s, t = normaliser(saisie), normaliser(attendu)
    if not s or not t:
        return "faux"

    def colle(x: str) -> str:
        return x.replace(" ", "")

    lettres = len(colle(t))
    au_plus = max(lettres // JUGEMENT.lettres_par_faute, lettres * JUGEMENT.presque)
    pleins = colle(normaliser(saisie, articles=False)), colle(normaliser(attendu, articles=False))
    n = min(_fautes_au_plus(s, t, au_plus), _fautes_au_plus(colle(s), colle(t), au_plus), _fautes_au_plus(*pleins, au_plus))
    if n <= lettres // JUGEMENT.lettres_par_faute:
        return "juste"
    os, ot = colle(a_l_oreille(s)), colle(a_l_oreille(t))
    a_l_oreille_au_plus = len(ot) // JUGEMENT.lettres_par_faute_a_l_oreille
    if _fautes_au_plus(os, ot, a_l_oreille_au_plus) <= a_l_oreille_au_plus:
        return "juste"
    if n <= lettres * JUGEMENT.presque:
        return "presque"
    morceau = len(colle(s)) >= lettres * JUGEMENT.morceau and s in t
    return "presque" if morceau or t in s else "faux"
