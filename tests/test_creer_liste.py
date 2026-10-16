"""`creer_liste` et la ressource d'une liste, appelés comme un vrai client, contre les réponses enregistrées chez Deezer."""

import json

import pytest
from mcp import Client
from mcp.types import TextResourceContents

from honear_mcp.reseau.rangement import Rangement
from tests.demandes import AUTOUR_DE_BELLA, DAFT_PUNK, GIMS, INCONNU, PEU_CONNUES, QUEEN_MAL_ECRIT, STROMAE, creer, par_id, refus
from tests.faux_deezer import FauxDeezer

pytestmark = pytest.mark.anyio


async def test_une_liste_des_pistes_trouvees_se_range_du_plus_connu_au_moins_connu(
    client: Client, faux_deezer: FauxDeezer, rangement: Rangement
) -> None:
    await client.call_tool("chercher_titres", {"titres": [DAFT_PUNK, STROMAE, GIMS, QUEEN_MAL_ECRIT]})
    liste = await creer(
        client,
        [
            par_id(
                3135553, "Daft Punk", "One More Time", surnoms={"artiste": ["Daft Punk", "Les Daft"]}, anecdote="Un clip animé."
            ),
            par_id(6297555, "Stromae", "Alors on danse"),
            par_id(72717420, "GIMS", "Bella", surnoms={"artiste": ["Maître Gims", "maitre gims"]}),
            par_id(4091936671, "Queen", "Bohemian Rhapsody"),
            par_id(4091936641, "Queen", "Killer Queen"),
            par_id(4091936741, "Queen", "I Want To Break Free"),
            par_id(98356886, "Kendji Girac", "Bella"),
            par_id(3135553, "Daft Punk", "One More Time"),
            *AUTOUR_DE_BELLA,
        ],
    )
    # Les pistes vues par chercher_titres ne rappellent pas Deezer.
    assert len(faux_deezer.appels) == 4
    assert [p.deezer for p in liste.pistes] == [
        6297555,
        72717420,
        3135553,
        4091936641,
        571858272,
        126024227,
        4091936741,
        98356886,
        2992386141,
        3154947201,
        68893313,
    ]
    assert [(e.titre, e.raison) for e in liste.ecartees] == [
        ("One More Time", "doublon"),
        ("Bohemian Rhapsody", "artiste_deja_present"),
    ]
    daft_punk, gims = liste.pistes[2], liste.pistes[1]
    assert (daft_punk.surnoms.artiste, daft_punk.anecdote) == (["Les Daft"], "Un clip animé.")
    # Honear accepte déjà « Maître Gims » pour « GIMS » : le surnom ne changerait rien.
    assert gims.surnoms.artiste == []
    assert liste.lien == f"https://honear.fr/?liste={liste.id}"
    assert liste.oubliee_le == "2026-11-15"
    rangee = rangement.lire(liste.id)
    assert rangee is not None
    assert rangee.dans_l_ordre
    assert rangee.pistes == liste.pistes


async def test_la_ressource_d_une_liste_la_rend_telle_que_honear_la_lira(client: Client, rangement: Rangement) -> None:
    await client.call_tool("chercher_titres", {"titres": [STROMAE, GIMS]})
    pistes = [
        par_id(6297555, "Stromae", "Alors on danse"),
        par_id(72717420, "GIMS", "Bella"),
        par_id(98356886, "Kendji Girac", "Bella"),
        par_id(1302152722, "GIMS", "BELLE"),
        par_id(3135553, "Daft Punk", "One More Time"),
        *AUTOUR_DE_BELLA,
    ]
    liste = await creer(client, pistes, ordre="telle_quelle")
    lue = await client.read_resource(f"honear://listes/{liste.id}")
    (contenu,) = lue.contents
    assert isinstance(contenu, TextResourceContents)
    assert json.loads(contenu.text)["dans_l_ordre"] is False
    attendues = [6297555, 72717420, 98356886, 1302152722, 3135553, *(p["deezer"] for p in AUTOUR_DE_BELLA)]
    assert [p["deezer"] for p in json.loads(contenu.text)["pistes"]] == attendues


async def test_trop_peu_de_pistes_jouables_n_enregistre_rien_et_dit_pourquoi(client: Client, rangement: Rangement) -> None:
    texte = await refus(
        client,
        [
            DAFT_PUNK,
            INCONNU,
            par_id(1, "Personne", "Rien"),
            par_id(3157687, "Daft Punk", "One More Time (12 Mix)"),
            GIMS,
            *PEU_CONNUES,
        ],
        seulement_connus=True,
    )
    assert "il reste 2 pistes jouables" in texte
    assert "Zqxwv Plughxyz — Vwqzk Trlmpf : introuvable" in texte
    assert "Personne — Rien : introuvable" in texte
    assert "peu_connue" in texte
    assert rangement.nombre() == 0
