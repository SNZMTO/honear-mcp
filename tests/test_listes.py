"""Les listes, hors du protocole : le texte nettoyé, les surnoms utiles, le rangement sur le disque et sa durée de vie."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from honear_mcp.regles.liste import Liste, NomDeListe, PisteDeLaListe, PisteDemandee, Surnoms, surnoms_utiles
from honear_mcp.regles.nettoyage import nettoyer
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages import LISTES
from tests.fausse_horloge import FausseHorloge

PISTES = [
    PisteDeLaListe(deezer=n, titre=f"Titre {n}", artiste="Artiste", rang=n, surnoms=Surnoms(), anecdote="")
    for n in range(LISTES.pistes_au_moins)
]


def test_un_texte_qui_finira_sur_un_ecran_perd_ce_qui_agit_sans_se_voir() -> None:
    assert nettoyer("Soirée\u202e de Léa\u200f") == "Soirée de Léa"
    assert nettoyer("Café \u0007  crème\n\nhttps://pirate.example/x www.pub.example") == "Café crème"
    assert nettoyer("Les 30 ans de Léa 🎉") == "Les 30 ans de Léa 🎉"


def test_un_nom_de_liste_vide_une_fois_nettoye_ou_trop_long_est_refuse() -> None:
    nom = TypeAdapter(NomDeListe)
    assert nom.validate_python("  Les 30 ans de Léa ") == "Les 30 ans de Léa"
    for refuse in ["\u202e\u200f", "https://pirate.example", "x" * (LISTES.nom_au_plus + 1)]:
        with pytest.raises(ValidationError):
            nom.validate_python(refuse)


def test_une_piste_demandee_borne_ses_surnoms_et_son_anecdote() -> None:
    trop = {"artiste": "GIMS", "titre": "Bella"}
    with pytest.raises(ValidationError):
        PisteDemandee.model_validate({**trop, "surnoms": {"artiste": ["a", "b", "c", "d"]}})
    with pytest.raises(ValidationError):
        PisteDemandee.model_validate({**trop, "anecdote": "x" * (LISTES.anecdote_au_plus + 1)})


def test_un_surnom_que_le_jugement_de_honear_accepte_deja_est_oublie() -> None:
    gims = Surnoms(artiste=["GIMS", "Maître Gims"], titre=["Bella !", "\u200f"])
    assert surnoms_utiles(gims, "GIMS", "Bella") == Surnoms(artiste=[], titre=[])
    m = Surnoms(artiste=["-m-", "Matthieu Chedid", "Mathieu Chédid"], titre=["Je dis aime"])
    assert surnoms_utiles(m, "-M-", "Je dis aime") == Surnoms(artiste=["Matthieu Chedid"], titre=[])


def test_une_liste_rangee_se_relit_puis_s_oublie_si_personne_ne_la_joue(rangement: Rangement, horloge: FausseHorloge) -> None:
    liste = rangement.creer("Soirée", PISTES, dans_l_ordre=True)
    assert len(liste.id) == 16
    assert rangement.lire(liste.id) == liste
    horloge.heure += LISTES.vie
    assert rangement.lire(liste.id) is None
    assert rangement.nombre() == 0


def test_une_liste_jouee_vit_de_nouveau_toute_une_vie(rangement: Rangement, horloge: FausseHorloge) -> None:
    liste = rangement.creer("Soirée", PISTES, dans_l_ordre=False)
    horloge.heure += LISTES.vie - 1
    jouee = rangement.jouee(liste.id)
    assert jouee is not None
    horloge.heure += LISTES.vie - 1
    assert rangement.lire(liste.id) == jouee


def test_un_identifiant_n_est_qu_un_nom_de_fichier(rangement: Rangement) -> None:
    for intrus in ["../listes", "..", "a/b", "", "x.json"]:
        assert rangement.lire(intrus) is None
        assert rangement.jouee(intrus) is None


def _remplir(rangement: Rangement, tmp_path: Path, *, jouees: bool) -> Liste:
    """Un rangement plein : une liste jouée, puis les autres, écrites d'un coup à côté d'elle (le dossier est celui de la
    fixture), chacune un peu plus jeune que la précédente."""
    premiere = rangement.creer("Soirée", PISTES, dans_l_ordre=True)
    jouee = rangement.jouee(premiere.id)
    assert jouee is not None
    for n in range(LISTES.listes_au_plus - 1):
        autre = {**premiere.model_dump(), "id": f"liste{n}", "jouee": jouees, "jusqua": premiere.jusqua + 1 + n}
        (tmp_path / "listes" / f"liste{n}.json").write_text(json.dumps(autre))
    return jouee


def test_un_rangement_plein_fait_de_la_place_en_oubliant_la_plus_vieille_que_personne_n_a_jouee(
    rangement: Rangement, tmp_path: Path
) -> None:
    jouee = _remplir(rangement, tmp_path, jouees=False)
    nouvelle = rangement.creer("Une de plus", PISTES, dans_l_ordre=True)
    assert rangement.nombre() == LISTES.listes_au_plus
    assert rangement.lire("liste0") is None
    assert rangement.lire("liste1") is not None
    assert rangement.lire(jouee.id) == jouee
    assert rangement.lire(nouvelle.id) == nouvelle


def test_un_rangement_plein_de_listes_jouees_oublie_celle_qui_s_oublierait_la_premiere(
    rangement: Rangement, tmp_path: Path
) -> None:
    jouee = _remplir(rangement, tmp_path, jouees=True)
    rangement.creer("Une de plus", PISTES, dans_l_ordre=True)
    assert rangement.nombre() == LISTES.listes_au_plus
    assert rangement.lire(jouee.id) is None
    assert rangement.lire("liste0") is not None
