"""Le mini blind test, joué comme une fenêtre MCP Apps le joue, contre les réponses enregistrées chez Deezer ; et ce qu'en reçoit
un client qui ne sait pas afficher de fenêtre."""

from collections.abc import AsyncIterator

import pytest
from mcp import Client
from mcp.client.extension import advertise
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID
from mcp.types import CallToolResult, TextResourceContents

from honear_mcp.regles.liste import Liste, PisteDeLaListe, Surnoms
from honear_mcp.regles.mini import PartieDuMini
from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages_du_mini import MINI
from honear_mcp.ressources.textes_du_mini import TEXTES_DU_MINI as T
from honear_mcp.serveurs.public import creer_le_serveur
from tests.fausse_horloge import FausseHorloge

pytestmark = pytest.mark.anyio

DAFT_PUNK = {"artiste": "Daft Punk", "titre": "One More Time"}
STROMAE = {"artiste": "Stromae", "titre": "Alors on danse"}
GIMS = {"artiste": "Gims", "titre": "Bella"}
INCONNU = {"artiste": "Zqxwv Plughxyz", "titre": "Vwqzk Trlmpf"}
PISTES = [(3135553, "One More Time", "Daft Punk"), (6297555, "Alors on danse", "Stromae"), (72717420, "Bella", "GIMS")]


@pytest.fixture
async def fenetre(deezer: Deezer, rangement: Rangement, parties: Parties) -> AsyncIterator[Client]:
    """Un client qui sait afficher une fenêtre MCP Apps : il le dit dans ses capacités, comme claude.ai."""
    apps = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})
    async with Client(creer_le_serveur(deezer, rangement, parties), raise_exceptions=True, extensions=[apps]) as client:
        await client.call_tool("chercher_titres", {"titres": [DAFT_PUNK, STROMAE, GIMS]})
        yield client


@pytest.fixture
def liste(rangement: Rangement) -> Liste:
    pistes = [PisteDeLaListe(deezer=d, titre=t, artiste=a, rang=1, surnoms=Surnoms(), anecdote="") for d, t, a in PISTES]
    pistes[0] = pistes[0].model_copy(update={"anecdote": "Le clip est un dessin animé."})
    return rangement.creer("Les années 2000", pistes, dans_l_ordre=True)


def contenu(resultat: CallToolResult) -> dict[str, object]:
    assert not resultat.is_error, resultat.content
    assert isinstance(resultat.structured_content, dict)
    return resultat.structured_content


async def test_le_modele_ne_voit_que_jouer_ici_et_la_fenetre_a_ses_trois_outils(fenetre: Client) -> None:
    outils = {o.name: o for o in (await fenetre.list_tools()).tools}
    assert (outils["jouer_ici"].meta or {})["ui"] == {"resourceUri": MINI.fenetre}
    for nom in ("mini_piste", "mini_repondre", "mini_reveler"):
        assert (outils[nom].meta or {})["ui"] == {"resourceUri": MINI.fenetre, "visibility": ["app"]}


async def test_la_fenetre_a_l_allure_de_honear_et_ne_charge_que_deezer_et_ses_polices(fenetre: Client) -> None:
    (page,) = (await fenetre.read_resource(MINI.fenetre)).contents
    assert isinstance(page, TextResourceContents)
    assert page.mime_type == APP_MIME_TYPE
    assert (page.meta or {})["ui"]["csp"] == {"resourceDomains": list(MINI.domaines)}
    assert "--miel: #E2A72E;" in page.text
    assert f"{MINI.site}/polices/caprasimo-400.woff2" in page.text
    assert "mini_reveler" in page.text
    assert "__" + "SCRIPT__" not in page.text


async def test_une_partie_de_bout_en_bout_sans_que_le_modele_lise_une_reponse(
    fenetre: Client, liste: Liste, rangement: Rangement
) -> None:
    ouverte = await fenetre.call_tool("jouer_ici", {"liste": liste.id, "pistes": 3})
    prete = contenu(ouverte)
    jouee = rangement.lire(liste.id)
    assert jouee is not None
    assert jouee.jouee
    assert (prete["nom"], prete["total"]) == ("Les années 2000", 3)
    for _, un_titre, un_artiste in PISTES:
        assert un_titre not in ouverte.model_dump_json()
        assert un_artiste not in ouverte.model_dump_json()
    partie = prete["partie"]
    piste = contenu(await fenetre.call_tool("mini_piste", {"partie": partie}))
    assert (piste["rang"], piste["total"]) == (1, 3)
    assert str(piste["extrait"]).startswith("https://cdnt-preview.dzcdn.net/")
    assert "One More Time" not in str(piste)
    artiste = contenu(await fenetre.call_tool("mini_repondre", {"partie": partie, "saisie": "dafte punk"}))
    assert (artiste["trouve"], artiste["verdict"], artiste["points"]) == (["artiste"], "juste", 1)
    titre = contenu(await fenetre.call_tool("mini_repondre", {"partie": partie, "saisie": "one more time"}))
    assert (titre["trouve"], titre["points"]) == (["artiste", "titre"], 2)
    revelee = contenu(await fenetre.call_tool("mini_reveler", {"partie": partie}))
    assert (revelee["titre"], revelee["artiste"], revelee["anecdote"]) == (
        "One More Time",
        "Daft Punk",
        "Le clip est un dessin animé.",
    )
    assert str(revelee["pochette"]).startswith("https://cdn-images.dzcdn.net/images/cover/")
    assert (revelee["points"], revelee["finie"]) == (2, False)
    for _ in range(2):
        derniere = contenu(await fenetre.call_tool("mini_reveler", {"partie": partie}))
    assert (derniere["rang"], derniere["finie"], derniere["points"]) == (3, True, 2)
    apres = await fenetre.call_tool("mini_piste", {"partie": partie})
    assert apres.is_error


async def test_une_partie_de_titres_pour_un_theme_passe_ceux_que_deezer_n_a_pas(fenetre: Client) -> None:
    prete = contenu(await fenetre.call_tool("jouer_ici", {"titres": [DAFT_PUNK, STROMAE, GIMS, INCONNU]}))
    assert prete["total"] == 3
    trop_peu = await fenetre.call_tool("jouer_ici", {"titres": [DAFT_PUNK, INCONNU]})
    les_deux = await fenetre.call_tool("jouer_ici", {"titres": [DAFT_PUNK], "liste": "x"})
    assert trop_peu.is_error
    assert les_deux.is_error


async def test_une_partie_s_oublie_une_heure_apres_son_dernier_geste(
    fenetre: Client, liste: Liste, horloge: FausseHorloge
) -> None:
    partie = contenu(await fenetre.call_tool("jouer_ici", {"liste": liste.id}))["partie"]
    horloge.heure += MINI.vie - 1
    assert not (await fenetre.call_tool("mini_piste", {"partie": partie})).is_error
    horloge.heure += MINI.vie
    oubliee = await fenetre.call_tool("mini_piste", {"partie": partie})
    assert oubliee.is_error
    assert T.inconnue in oubliee.model_dump_json()


async def test_un_appel_qui_ne_dit_pas_la_fenetre_ouvre_la_partie_avec_le_lien_et_seule_la_fenetre_la_joue(
    client: Client, liste: Liste
) -> None:
    # claude.ai montre la fenêtre sans le dire dans l'appel de jouer_ici : la partie s'ouvre, et le lien est là au cas où.
    sans = contenu(await client.call_tool("jouer_ici", {"liste": liste.id}))
    assert sans["total"] == len(PISTES)
    assert f"https://honear.fr/?liste={liste.id}" in str(sans["message"])
    titres = contenu(await client.call_tool("jouer_ici", {"titres": [DAFT_PUNK, STROMAE, GIMS]}))
    assert str(titres["message"]).endswith(T.sans_fenetre_titres)
    # Les outils de la fenêtre, eux, ne répondent qu'à un client qui dit savoir la montrer : pas au modèle.
    refus = await client.call_tool("mini_reveler", {"partie": str(sans["partie"])})
    assert refus.is_error
    assert T.reservee in refus.model_dump_json()


def test_plein_le_mini_oublie_la_plus_vieille_partie_jamais_jouee_et_refuse_quand_toutes_ont_ete_jouees() -> None:
    horloge = FausseHorloge()
    parties = Parties(horloge)
    partie = PartieDuMini(nom="Soirée", pistes=[])
    ouvertes = []
    for _ in range(MINI.parties_au_plus):
        ouvertes.append(parties.ouvrir(partie))
        horloge.heure += 1
    # Une partie qu'on joue garde sa place ; la plus vieille jamais jouée laisse la sienne à la nouvelle.
    jouee = ouvertes[0]
    assert jouee is not None
    parties.garder(jouee, partie)
    nouvelle = parties.ouvrir(partie)
    assert nouvelle is not None
    assert parties.en_cours == MINI.parties_au_plus
    assert parties.lire(jouee) is not None
    assert ouvertes[1] is not None
    assert parties.lire(ouvertes[1]) is None
    # Toutes jouées : on refuse, plutôt que de chasser une partie en cours.
    for ouverte in [*ouvertes, nouvelle]:
        if ouverte is not None and parties.lire(ouverte) is not None:
            parties.garder(ouverte, partie)
    assert parties.ouvrir(partie) is None
