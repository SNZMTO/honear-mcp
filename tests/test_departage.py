"""Un titre ambigu dans `creer_liste` : ses candidats rendus au modèle quand le client ne sait pas montrer de formulaire, ou la
question posée à la personne, sur les deux protocoles, et ce qui se passe quand elle choisit, écarte ou refuse."""

import pytest
from mcp import Client
from mcp.client.context import ClientRequestContext
from mcp.client.session import ElicitationFnT
from mcp.types import ElicitRequestFormParams, ElicitRequestParams, ElicitResult, ErrorData

from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.serveurs.public import creer_le_serveur
from tests.demandes import AUTOUR_DE_BELLA, DAFT_PUNK, GIMS, QUEEN_MAL_ECRIT, STROMAE, creer, par_id, refus
from tests.fausse_horloge import FausseHorloge

pytestmark = pytest.mark.anyio


async def test_un_titre_ambigu_sans_formulaire_rend_ses_candidats_au_modele(client: Client, rangement: Rangement) -> None:
    texte = await refus(
        client, [QUEEN_MAL_ECRIT, DAFT_PUNK, STROMAE, GIMS, par_id(98356886, "Kendji Girac", "Bella"), *AUTOUR_DE_BELLA]
    )
    assert "Queen — Bohemian Rapsody : 4091936671 (Bohemian Rhapsody, Queen" in texte
    assert rangement.nombre() == 0


def repondre(choix: str, vues: list[ElicitRequestFormParams]) -> ElicitationFnT:
    # Les noms et le type rendu sont ceux qu'attend le SDK (ElicitationFnT).
    async def elicitation(context: ClientRequestContext, params: ElicitRequestParams) -> ElicitResult | ErrorData:
        assert isinstance(params, ElicitRequestFormParams)
        vues.append(params)
        (champ,) = params.requested_schema["properties"]
        return ElicitResult(action="accept", content={champ: choix}) if choix else ElicitResult(action="decline")

    return elicitation


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize(("choix", "attendue"), [("4091936671", 4091936671), ("aucun", None)])
async def test_un_titre_ambigu_se_fait_departager_par_l_hote(
    deezer: Deezer, rangement: Rangement, mode: str, choix: str, attendue: int | None
) -> None:
    vues: list[ElicitRequestFormParams] = []
    serveur = creer_le_serveur(deezer, rangement, Parties(FausseHorloge()))
    async with Client(serveur, raise_exceptions=True, mode=mode, elicitation_callback=repondre(choix, vues)) as client:
        pistes = [
            QUEEN_MAL_ECRIT,
            DAFT_PUNK,
            STROMAE,
            GIMS,
            par_id(98356886, "Kendji Girac", "Bella"),
            par_id(1302152722, "GIMS", "BELLE"),
            *AUTOUR_DE_BELLA,
        ]
        liste = await creer(client, pistes)
    (question,) = vues
    proprietes = question.requested_schema["properties"]
    assert proprietes["titre_0"]["title"] == "Queen — Bohemian Rapsody"
    assert [o["const"] for o in proprietes["titre_0"]["oneOf"]][:2] == ["4091936671", "4091936771"]
    if attendue is None:
        assert ("Bohemian Rapsody", "ecartee_par_l_hote") in [(e.titre, e.raison) for e in liste.ecartees]
    else:
        assert attendue in [p.deezer for p in liste.pistes]


async def test_un_hote_qui_refuse_de_departager_n_enregistre_rien(deezer: Deezer, rangement: Rangement) -> None:
    vues: list[ElicitRequestFormParams] = []
    async with Client(
        creer_le_serveur(deezer, rangement, Parties(FausseHorloge())), elicitation_callback=repondre("", vues)
    ) as client:
        pistes = [QUEEN_MAL_ECRIT, DAFT_PUNK, STROMAE, GIMS, par_id(98356886, "Kendji Girac", "Bella"), *AUTOUR_DE_BELLA]
        texte = await refus(client, pistes)
    assert "4091936671" in texte
    assert rangement.nombre() == 0
