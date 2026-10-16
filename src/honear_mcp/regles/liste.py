"""Une liste sur mesure : ce que le modèle demande pour chaque piste, ce qu'on en garde, et dans quel ordre Honear la joue.

Le modèle propose ; la règle écarte ce qui jouerait mal (un doublon, un titre peu connu quand on n'en veut que des connus, un
artiste déjà assez présent) et range du plus connu au moins connu quand la difficulté monte. Les surnoms que le jugement de
Honear accepte déjà sont oubliés : ils ne changeraient rien.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from honear_mcp.regles.nettoyage import nettoyer
from honear_mcp.regles.parties import Partie, juger_les_parties
from honear_mcp.regles.titres import Nom, comparable
from honear_mcp.ressources.reglages import LISTES


def _pas_vide(texte: str) -> str:
    if not texte:
        raise ValueError(texte)
    return texte


type NomDeListe = Annotated[
    str, StringConstraints(max_length=LISTES.nom_au_plus), AfterValidator(nettoyer), AfterValidator(_pas_vide)
]
type Surnom = Annotated[str, StringConstraints(max_length=LISTES.surnom_au_plus), AfterValidator(nettoyer)]
type Anecdote = Annotated[str, StringConstraints(max_length=LISTES.anecdote_au_plus), AfterValidator(nettoyer)]
type Raison = Literal["introuvable", "sans_extrait", "doublon", "peu_connue", "artiste_deja_present", "ecartee_par_l_hote"]
"""Pourquoi une piste demandée n'est pas dans la liste."""


class Surnoms(BaseModel):
    """D'autres façons justes de dire l'artiste ou le titre, que Honear accepte en plus du vrai nom."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    artiste: Annotated[list[Surnom], Field(max_length=LISTES.surnoms_au_plus)] = []
    """« Matthieu Chedid » pour « -M- »."""
    titre: Annotated[list[Surnom], Field(max_length=LISTES.surnoms_au_plus)] = []
    """Un titre qu'on appelle autrement : « Le Connemara » pour « Les Lacs du Connemara »."""


class PisteDemandee(BaseModel):
    """Une piste que le modèle veut dans la liste."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    artiste: Nom
    titre: Nom
    deezer: int | None = None
    """L'identifiant que `chercher_titres` a donné : la piste exacte, sans rien rechercher. Sans lui, on la cherche."""
    surnoms: Surnoms = Surnoms()
    anecdote: Anecdote = ""
    """Une phrase courte et vérifiable, montrée à la révélation : « Enregistrée en une prise, à 3 heures du matin. »"""


class PisteDeLaListe(BaseModel):
    """Une piste gardée : ce que Honear relira chez Deezer par son identifiant, et ce qu'il ajoutera au jugement et à l'écran."""

    model_config = ConfigDict(frozen=True)

    deezer: int
    titre: str
    artiste: str
    rang: int
    surnoms: Surnoms
    anecdote: str


class Liste(BaseModel):
    """Une liste enregistrée, telle que Honear la lit."""

    model_config = ConfigDict(frozen=True)

    id: str
    nom: str
    dans_l_ordre: bool
    """Vrai quand la difficulté monte : Honear la joue alors dans cet ordre, sans la mélanger."""
    pistes: list[PisteDeLaListe]
    jusqua: float
    """Quand elle sera oubliée, en secondes depuis 1970, si personne ne la joue d'ici là."""
    jouee: bool = False
    """Vrai dès qu'une partie l'a jouée, sur Honear ou dans la fenêtre du mini blind test : quand le rangement est plein, on
    oublie d'abord une liste que personne n'a jouée."""


class Ecartee(BaseModel):
    """Une piste demandée qui n'est pas dans la liste, et pourquoi."""

    model_config = ConfigDict(frozen=True)

    artiste: str
    titre: str
    raison: Raison


def surnoms_utiles(surnoms: Surnoms, artiste: str, titre: str) -> Surnoms:
    """Les surnoms qui changent quelque chose : ceux que la saisie libre de Honear ne trouve pas déjà avec le vrai nom (« Maître
    Gims » vaut déjà « GIMS ») ni avec un surnom gardé avant eux ; ni ceux que le nettoyage a vidés."""

    def utiles(liste: list[str], vrai: str, partie: Partie) -> list[str]:
        gardes: list[str] = []
        for surnom in liste:
            trouve, _ = juger_les_parties(surnom, [partie], {partie: [vrai, *gardes]}, [])
            if surnom and not trouve:
                gardes.append(surnom)
        return gardes

    return Surnoms(artiste=utiles(surnoms.artiste, artiste, "artiste"), titre=utiles(surnoms.titre, titre, "titre"))


def ranger(
    pistes: list[PisteDeLaListe], *, croissante: bool, seulement_connus: bool, artiste_au_plus: int
) -> tuple[list[PisteDeLaListe], list[tuple[PisteDeLaListe, Raison]]]:
    """Les pistes gardées, dans l'ordre où Honear les jouera, et celles qu'on écarte avec leur raison.

    Quand la difficulté monte, on range du plus connu au moins connu avant de compter les artistes : d'un artiste trop
    présent, on garde ses titres les plus connus.
    """
    ordonnees = sorted(pistes, key=lambda p: -p.rang) if croissante else pistes
    gardees: list[PisteDeLaListe] = []
    ecartees: list[tuple[PisteDeLaListe, Raison]] = []
    vues: set[int] = set()
    par_artiste: dict[str, int] = {}
    for piste in ordonnees:
        artiste = comparable(piste.artiste)
        if piste.deezer in vues:
            ecartees.append((piste, "doublon"))
        elif seulement_connus and piste.rang < LISTES.connu_au_moins:
            ecartees.append((piste, "peu_connue"))
        elif par_artiste.get(artiste, 0) >= artiste_au_plus:
            ecartees.append((piste, "artiste_deja_present"))
        else:
            gardees.append(piste)
            par_artiste[artiste] = par_artiste.get(artiste, 0) + 1
        vues.add(piste.deezer)
    return gardees, ecartees
