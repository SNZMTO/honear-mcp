"""Ce que Deezer répond, lu sans jamais l'appeler : ses pistes, ses refus, et l'adresse d'une recherche.

C'est le réseau (`reseau/deezer.py`) qui demande. Les champs gardent les noms que Deezer leur donne : ce module est la frontière.
"""

import re
from typing import Literal
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from honear_mcp.regles.titres import nom_nu
from honear_mcp.ressources.deezer import API_DE_DEEZER
from honear_mcp.ressources.reglages import DEEZER


class ArtisteDeDeezer(BaseModel):
    """L'artiste principal d'une piste."""

    name: str


class AlbumDeDeezer(BaseModel):
    """L'album d'une piste."""

    title: str = ""
    cover_medium: str = ""
    """Sa pochette, en 250 pixels de côté."""


class PisteDeDeezer(BaseModel):
    """Une piste, telle qu'une recherche la donne : on ne garde que ce qu'on lit."""

    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    """Le titre complet, version comprise : « Alors on danse (Radio Edit) »."""
    title_short: str = ""
    """Le titre sans sa version : « Alors on danse »."""
    title_version: str | None = None
    duration: int = 0
    """En secondes."""
    rank: int = 0
    """La popularité selon Deezer : plus c'est haut, plus c'est écouté."""
    readable: bool = True
    preview: str = ""
    """L'extrait de 30 secondes, un lien signé qui expire ; vide quand Deezer n'en a pas."""
    artist: ArtisteDeDeezer
    album: AlbumDeDeezer = AlbumDeDeezer()


class _ErreurDeDeezer(BaseModel):
    code: int = 0


class _Reponse(BaseModel):
    data: list[JsonValue] = []
    error: _ErreurDeDeezer | None = None


type Refus = Literal["quota", "introuvable", "autre"]
"""Ce que Deezer dit quand il refuse : trop d'appels (il faut ralentir), rien à cette adresse, ou autre chose."""


def _lire(corps: bytes) -> _Reponse | None:
    try:
        return _Reponse.model_validate_json(corps)
    except ValidationError:
        return None


def refus_de(corps: bytes) -> Refus | None:
    """Le refus que porte une réponse de Deezer, rien si elle est bonne, « autre » si ce n'est pas une réponse de Deezer."""
    reponse = _lire(corps)
    if reponse is None:
        return "autre"
    if reponse.error is None:
        return None
    if reponse.error.code == API_DE_DEEZER.quota:
        return "quota"
    return "introuvable" if reponse.error.code in API_DE_DEEZER.introuvable else "autre"


def lire_les_pistes(corps: bytes) -> list[PisteDeDeezer]:
    """Les pistes d'une réponse, dans l'ordre de Deezer, sauf celles qui n'ont pas de quoi être lues (un titre, un artiste)."""
    reponse = _lire(corps)
    pistes: list[PisteDeDeezer] = []
    for donnee in reponse.data if reponse is not None else []:
        try:
            pistes.append(PisteDeDeezer.model_validate(donnee))
        except ValidationError:
            continue
    return pistes


def lire_la_piste(corps: bytes) -> PisteDeDeezer | None:
    """La piste qu'une fiche (`/track/{id}`) décrit, ou rien si Deezer n'en a pas à cet identifiant."""
    try:
        return PisteDeDeezer.model_validate_json(corps)
    except ValidationError:
        return None


def adresse_de_la_piste(deezer: int) -> str:
    """L'adresse de la fiche d'une piste, depuis l'API."""
    return f"/track/{deezer}"


def adresse_de_recherche(artiste: str, titre: str) -> str:
    """L'adresse où chercher un titre, depuis l'API : son artiste et son nom, sans ce qui l'habille, en vrac.

    La recherche avancée de Deezer (`artist:"…" track:"…"`) ne trouve plus rien : la recherche en vrac la remplace, et c'est la
    comparaison des noms qui trie ensuite.
    """
    q = f"{artiste} {nom_nu(titre)}"
    return f"/search/track?{urlencode({'q': q, 'limit': DEEZER.resultats}, quote_via=quote)}"


_POCHETTE = re.compile(r"https://[a-z0-9-]+\.dzcdn\.net/images/cover/[0-9a-f]{32}/\d{2,4}x\d{2,4}-[0-9a-z-]+\.jpg")
_EXPIRATION = re.compile(r"[?&~=]exp=(\d{9,12})(?!\d)")


def pochette_de(piste: PisteDeDeezer) -> str | None:
    """L'image de la pochette d'une piste, telle que Deezer la sert, de chez lui ; rien d'une autre adresse."""
    return piste.album.cover_medium if _POCHETTE.fullmatch(piste.album.cover_medium) else None


def expiration_de(extrait: str) -> float | None:
    """L'heure où expire le lien d'un extrait, en secondes depuis 1970, s'il la porte : Deezer signe ses liens pour un temps."""
    trouvee = _EXPIRATION.search(extrait)
    return float(trouvee.group(1)) if trouvee else None
