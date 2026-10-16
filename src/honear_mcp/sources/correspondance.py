"""Ce qu'une recherche chez Deezer dit d'un titre demandé : trouvé, ambigu ou introuvable, et ce qui le jouerait mal.

Un titre est trouvé quand une piste a son nom et son artiste, à l'habillage près (la règle de Honear) : on prend alors celle qui
n'a pas de drapeau, la plus populaire. Sinon, les pistes qui lui ressemblent le plus sont des candidats, à départager par le
modèle ; et si rien ne lui ressemble assez, il est introuvable. Mieux vaut un candidat de trop qu'une autre chanson à deviner.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from honear_mcp.regles.titres import Drapeau, TitreCherche, drapeaux_du_titre, nom_nu, proches, ressemblance, titre_montre
from honear_mcp.ressources.reglages import TITRES
from honear_mcp.sources.deezer import PisteDeDeezer


class Piste(BaseModel):
    """Une piste de Deezer, telle que le blind test la ferait écouter."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    deezer: int
    """Son identifiant chez Deezer."""
    titre: str
    """Le titre que Honear montre et attend : sans son invité ni ce qui dit son édition."""
    titre_complet: str
    """Le titre chez Deezer, version comprise : « Alors on danse (Radio Edit) »."""
    artiste: str
    album: str
    rang: int
    """Sa popularité chez Deezer : plus c'est haut, plus c'est écouté."""
    duree: int
    """En secondes."""
    drapeaux: list[Drapeau]
    """Ce qui la jouerait mal au blind test ; vide quand rien ne cloche."""


class Trouve(BaseModel):
    """Le titre est chez Deezer : voici la piste à jouer."""

    model_config = ConfigDict(frozen=True)

    etat: Literal["trouve"] = "trouve"
    cherche: TitreCherche
    piste: Piste


class Ambigu(BaseModel):
    """Aucune piste n'a ce nom et cet artiste, mais certaines y ressemblent : la plus proche d'abord."""

    model_config = ConfigDict(frozen=True)

    etat: Literal["ambigu"] = "ambigu"
    cherche: TitreCherche
    candidats: list[Piste]


class Introuvable(BaseModel):
    """Rien chez Deezer ne ressemble assez à ce titre."""

    model_config = ConfigDict(frozen=True)

    etat: Literal["introuvable"] = "introuvable"
    cherche: TitreCherche


type Resultat = Annotated[Trouve | Ambigu | Introuvable, Field(discriminator="etat")]


def piste_de(piste: PisteDeDeezer) -> Piste:
    """La piste telle qu'on la rend, avec ses drapeaux : sans extrait quand Deezer n'en donne pas ou ne la laisse pas lire."""
    drapeaux = drapeaux_du_titre(piste.title, piste.title_version or "", piste.artist.name)
    if not piste.readable or not piste.preview.startswith("https://"):
        drapeaux.add("sans_extrait")
    return Piste(
        deezer=piste.id,
        titre=titre_montre(piste.title_short or piste.title),
        titre_complet=piste.title,
        artiste=piste.artist.name,
        album=piste.album.title,
        rang=piste.rank,
        duree=piste.duration,
        drapeaux=sorted(drapeaux),
    )


def resultat_de(cherche: TitreCherche, pistes: list[PisteDeDeezer]) -> Resultat:
    """Ce que les pistes d'une recherche disent du titre cherché."""
    justes = [
        piste_de(p)
        for p in pistes
        if proches(nom_nu(p.title_short or p.title), nom_nu(cherche.titre)) and proches(p.artist.name, cherche.artiste)
    ]
    if justes:
        return Trouve(cherche=cherche, piste=min(justes, key=lambda p: (len(p.drapeaux) > 0, -p.rang)))
    voulu = f"{cherche.artiste} {nom_nu(cherche.titre)}"
    notees = [(ressemblance(voulu, f"{p.artist.name} {nom_nu(p.title_short or p.title)}"), p) for p in pistes]
    proches_assez = sorted(
        ((note, p) for note, p in notees if note >= TITRES.ressemblance_au_moins), key=lambda n: (-n[0], -n[1].rank)
    )
    if not proches_assez:
        return Introuvable(cherche=cherche)
    return Ambigu(cherche=cherche, candidats=[piste_de(p) for _, p in proches_assez[: TITRES.candidats_au_plus]])


def sans_doublons(resultats: list[Resultat]) -> list[Resultat]:
    """Les mêmes résultats, où une piste déjà trouvée plus haut porte le drapeau « doublon »."""
    vues: set[int] = set()
    marques: list[Resultat] = []
    for resultat in resultats:
        if not isinstance(resultat, Trouve):
            marques.append(resultat)
        elif resultat.piste.deezer in vues:
            piste = resultat.piste.model_copy(update={"drapeaux": sorted([*resultat.piste.drapeaux, "doublon"])})
            marques.append(resultat.model_copy(update={"piste": piste}))
        else:
            vues.add(resultat.piste.deezer)
            marques.append(resultat)
    return marques
