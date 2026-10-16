"""Ce qu'on lit dans le nom d'un titre : la comparaison, l'habillage, et les drapeaux de version."""

import pytest

from honear_mcp.regles.titres import Drapeau, comparable, drapeaux_du_titre, nom_nu, proches, ressemblance, titre_montre
from honear_mcp.ressources.reglages import TITRES


def test_deux_noms_se_comparent_sans_accents_ni_ponctuation() -> None:
    assert comparable("Céline Dion") == "celinedion"
    assert comparable("Simon & Garfunkel") == "simonandgarfunkel"
    assert comparable("-M-") == "m"


def test_un_nom_qui_contient_l_autre_est_proche() -> None:
    assert proches("Gims", "Maître Gims")
    assert proches("GIMS", "Gims")
    assert not proches("Daft Funk", "Daft Punk")
    assert not proches("", "Daft Punk")


def test_un_titre_perd_son_habillage_mais_jamais_tout() -> None:
    assert nom_nu("Bohemian Rhapsody - Remastered 2011") == "Bohemian Rhapsody"
    assert nom_nu("Alors on danse (Radio Edit)") == "Alors on danse"
    assert nom_nu("(Intro)") == "(Intro)"


def test_le_titre_montre_est_celui_que_honear_attend() -> None:
    assert titre_montre("Tout oublier (feat. Roméo Elvis)") == "Tout oublier"
    assert titre_montre("Runaway Train (2022 Remaster)") == "Runaway Train"
    assert titre_montre("Alors on danse - Radio Edit") == "Alors on danse"
    # Des parenthèses qui sont le titre restent.
    assert titre_montre("(I Can't Get No) Satisfaction") == "(I Can't Get No) Satisfaction"


def test_une_faute_de_frappe_ressemble_assez_pour_etre_proposee_une_autre_chanson_non() -> None:
    faute = ressemblance("Queen Bohemian Rapsody", "Queen Bohemian Rhapsody")
    autre_chanson = ressemblance("Queen Bohemian Rapsody", "Queen Killer Queen")
    assert faute >= TITRES.ressemblance_au_moins > autre_chanson


@pytest.mark.parametrize(
    ("titre", "version", "artiste", "drapeaux"),
    [
        ("One More Time", "", "Daft Punk", set()),
        ("Alors on danse (Radio Edit)", "(Radio Edit)", "Stromae", set()),
        ("Strobe (Original Mix)", "(Original Mix)", "deadmau5", set()),
        ("Alive", "", "Live", set()),
        ("Bohemian Rhapsody (Live Aid)", "(Live Aid)", "Queen", {"live"}),
        ("Ma direction (En concert)", "", "Sexion d'Assaut", {"live"}),
        ("One More Time (12 Mix)", "(12 Mix)", "Daft Punk", {"remix"}),
        ("Alors On Danse (Mowgli Remix)", "(Mowgli Remix)", "Stromae", {"remix"}),
        ("Alors on Danse Slowed", "", "Dybbukk", {"remix"}),
        ("One More Time (As Made Famous By Daft Punk)", "", "The Backing Tracks", {"karaoke"}),
        ("Je te promets", "", "Karaoké Party", {"karaoke"}),
        ("One More Time (Live at Hospitality In the Park 2016, Daft Punk Cover)", "", "London Elektricity", {"live", "reprise"}),
        ("Hallelujah", "", "Tribute to Jeff Buckley", {"reprise"}),
    ],
)
def test_la_version_d_une_piste_se_lit_dans_son_nom(titre: str, version: str, artiste: str, drapeaux: set[Drapeau]) -> None:
    assert drapeaux_du_titre(titre, version, artiste) == drapeaux
