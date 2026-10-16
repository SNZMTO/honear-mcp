"""Le portage du jugement de Honear, jugé contre la table que Honear a jugée lui-même (`tests/jugement-de-honear.json`, écrite
par `npm run exporter-pour-le-mcp` dans Honear, jamais retouchée ici) : si l'un des deux dérive, ce test rougit."""

import json
from pathlib import Path

import pytest

from honear_mcp.regles.jugement import a_l_oreille, fautes, juger, normaliser
from honear_mcp.regles.parties import Partie, cibles_de, juger_les_parties
from honear_mcp.ressources.honear import DEEZER_DE_HONEAR
from honear_mcp.ressources.reglages import DEEZER

TABLE = json.loads((Path(__file__).parent / "jugement-de-honear.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("cas", TABLE["juger"], ids=lambda c: f"{c['saisie']} → {c['attendu']}")
def test_une_saisie_jugee_comme_honear_la_juge(cas: dict[str, str]) -> None:
    assert normaliser(cas["saisie"]) == cas["normalise"]
    assert a_l_oreille(normaliser(cas["saisie"])) == cas["a_l_oreille"]
    assert juger(cas["saisie"], cas["attendu"]) == cas["verdict"]


@pytest.mark.parametrize("cas", TABLE["parties"], ids=lambda c: f"{c['texte']} → {c['artiste']}")
def test_une_saisie_libre_trouve_ce_que_honear_y_trouve(cas: dict[str, object]) -> None:
    feat = cas["feat"] if isinstance(cas["feat"], str) else None
    surnoms = cas["surnoms"] if isinstance(cas["surnoms"], dict) else {}
    parties: list[Partie] = ["artiste", "titre", "feat"] if feat is not None else ["artiste", "titre"]
    cibles = cibles_de(str(cas["artiste"]), str(cas["titre"]), feat, surnoms)
    deja = cas["deja"] if isinstance(cas["deja"], list) else []
    assert juger_les_parties(str(cas["texte"]), parties, cibles, deja) == (cas["trouve"], cas["verdict"])


def test_les_fautes_de_frappe_se_comptent_comme_dans_honear() -> None:
    assert (fautes("minuit", "minut"), fautes("minuit", "minuti"), fautes("demons", "deomns")) == (1, 1, 1)


def test_honear_et_le_mcp_ensemble_restent_sous_la_limite_de_deezer_avec_de_la_marge() -> None:
    assert DEEZER.fenetre == DEEZER_DE_HONEAR.fenetre
    # Deezer admet 50 appels par 5 secondes et par adresse : les deux ensemble en gardent 10 de côté.
    assert DEEZER.par_fenetre + DEEZER_DE_HONEAR.par_fenetre <= 40
