"""Ce qu'on lit dans le nom d'un titre : comment le comparer à un autre, ce qui n'est que son habillage, et ce qui le joue mal.

Les règles de comparaison et d'habillage viennent de Honear, qui s'en servait pour retrouver chez Deezer les titres d'une playlist
Spotify. Honear ne lit plus Spotify depuis le 16 octobre 2026 : elles ne vivent plus qu'ici.
"""

import difflib
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from honear_mcp.ressources.reglages import TITRES

type Nom = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TITRES.longueur_au_plus)]


class TitreCherche(BaseModel):
    """Un titre à retrouver chez Deezer, tel que le modèle le propose."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    artiste: Nom
    """L'artiste principal, comme on le dit : « Stromae », « Gims »."""
    titre: Nom
    """Le titre, sans sa version : « Alors on danse »."""


type Drapeau = Literal["sans_extrait", "live", "remix", "karaoke", "reprise", "doublon"]
"""Ce qui se joue mal au blind test : pas d'extrait à écouter, une version qui n'est pas l'original, un titre déjà demandé."""


def sans_accents(texte: str) -> str:
    """Le texte sans ses accents ni ses autres marques : « Céline » devient « Celine »."""
    return "".join(c for c in unicodedata.normalize("NFD", texte) if not unicodedata.category(c).startswith("M"))


def comparable(texte: str) -> str:
    """Une chaîne qu'on compare : en minuscules, sans accents, sans rien d'autre que ses lettres et ses chiffres."""
    return "".join(c for c in sans_accents(texte).lower().replace("&", "and") if c.isalnum())


_APRES_UN_TIRET = re.compile(r"\s+[-–—]\s+.*$")
_ENTRE_PARENTHESES = re.compile(r"\s*[(\[][^)\]]*[)\]]")


def nom_nu(titre: str) -> str:
    """Le nom d'un titre sans ce qui l'habille : ce qui suit un tiret (« - Remastered 2011 »), ce qui est entre parenthèses."""
    nu = _ENTRE_PARENTHESES.sub("", _APRES_UN_TIRET.sub("", titre)).strip()
    return nu or titre.strip()


def proches(un: str, autre: str) -> bool:
    """Vrai si deux noms disent la même chose, ou si l'un contient l'autre (« Gims » et « Maître Gims »)."""
    a, b = comparable(un), comparable(autre)
    return a != "" and b != "" and (a == b or a in b or b in a)


def ressemblance(un: str, autre: str) -> float:
    """Combien deux noms se ressemblent, de 0 à 1, une fois rendus comparables : « Bohemian Rapsody » et « Bohemian Rhapsody »."""
    return difflib.SequenceMatcher(None, comparable(un), comparable(autre)).ratio()


_INVITE = re.compile(r"\s*[(\[](?:feat\.?|ft\.?|featuring|avec)\s+[^)\]]+[)\]]", re.IGNORECASE)
_EDITION = (
    r"(?:remaster(?:ed)?|remix(?:ed)?|edit|version|live|mono|stereo|st[ée]r[ée]o|deluxe|anniversary|bonus|demo|explicit|single"
    r"|radio|original mix|mix)"
)
_EDITION_ENTRE_PARENTHESES = re.compile(rf"\s*[(\[][^)\]]*\b{_EDITION}\b[^)\]]*[)\]]", re.IGNORECASE)
_EDITION_APRES_UN_TIRET = re.compile(rf"\s+[-–—]\s+[^-–—]*\b{_EDITION}\b.*$", re.IGNORECASE)


def titre_montre(titre: str) -> str:
    """Le titre tel que Honear le montre et l'attend : sans son invité ni son édition (« Alors on danse (Radio Edit) »)."""
    sans_invite = _INVITE.sub("", titre)
    nu = _EDITION_APRES_UN_TIRET.sub("", _EDITION_ENTRE_PARENTHESES.sub("", sans_invite)).strip()
    return nu or titre.strip()


_LIVE = re.compile(r"\b(?:live|en (?:concert|public|direct)|unplugged)\b")
_REMIX = re.compile(r"\b(?:remix(?:ed|es)?|rmx|rework|bootleg|mash ?up|(?<!original )mix|slowed|sped up|nightcore)\b")
_KARAOKE = re.compile(r"\b(?:karaoke|backing tracks?|in the style of|made famous by|originally performed by|as performed by)\b")
_REPRISE = re.compile(r"\b(?:covers?|tribute|hommage|reprise)\b")


def drapeaux_du_titre(titre: str, version: str, artiste: str) -> set[Drapeau]:
    """Ce que le nom d'une piste dit de sa version : live, remix, karaoké ou reprise.

    Le live et le remix se lisent dans le titre et sa version ; le karaoké et la reprise aussi dans le nom de l'artiste (« The
    Backing Tracks », « Tribute Band »). Un groupe qui s'appelle « Live » n'est pas un live.
    """
    nom = sans_accents(f"{titre} {version}").lower()
    tout = sans_accents(f"{titre} {version} {artiste}").lower()
    drapeaux: set[Drapeau] = set()
    if _LIVE.search(nom):
        drapeaux.add("live")
    if _REMIX.search(nom):
        drapeaux.add("remix")
    if _KARAOKE.search(tout):
        drapeaux.add("karaoke")
    if _REPRISE.search(tout):
        drapeaux.add("reprise")
    return drapeaux
