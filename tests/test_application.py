"""L'application web, par HTTP mais sans réseau : `/sante`, le MCP sous ses seuls noms, son journal, et les listes que lit
Honear."""

import logging
from collections.abc import AsyncIterator
from importlib.metadata import version

import httpx2
import pytest

from honear_mcp.regles.liste import Liste, PisteDeLaListe, Surnoms
from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages import LISTES, SERVEUR
from honear_mcp.serveurs.public import application, application_interne
from tests.fausse_horloge import FausseHorloge

pytestmark = pytest.mark.anyio

INITIALISATION = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "essai", "version": "0"}},
}
EN_TETES_MCP = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
async def http(
    deezer: Deezer, rangement: Rangement, parties: Parties, horloge: FausseHorloge
) -> AsyncIterator[httpx2.AsyncClient]:
    """Un client HTTP branché à l'application dans le même processus, son cycle de vie démarré."""
    app = application(deezer, rangement, parties, horloge)
    async with (
        app.router.lifespan_context(app),
        httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8790") as client,
    ):
        yield client


async def test_sante_dit_si_le_serveur_attend_deezer(http: httpx2.AsyncClient) -> None:
    reponse = await http.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"deezer_en_attente": 0, "recherches_gardees": 0, "listes": 0, "parties": 0}


async def test_le_mcp_repond_sous_son_nom(http: httpx2.AsyncClient) -> None:
    reponse = await http.post("/mcp", json=INITIALISATION, headers=EN_TETES_MCP)
    assert reponse.status_code == 200
    assert f'"name":"honear","title":"Honear","version":"{version("honear-mcp")}"' in reponse.text


async def test_le_journal_dit_ce_que_fait_un_client_sans_garder_son_adresse(
    http: httpx2.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    fenetre = {"extensions": {"io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}}, "sampling": {}}
    client = {"name": "essai", "version": "0"}
    initialisation_de_claude = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": fenetre, "clientInfo": client},
    }
    lecture = {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "honear://listes/SECRET1234"}}
    with caplog.at_level(logging.INFO, logger="honear_mcp.journal"):
        await http.post("/mcp", json=initialisation_de_claude, headers={**EN_TETES_MCP, "User-Agent": "Claude-User"})
        await http.post("/mcp", json=lecture, headers=EN_TETES_MCP)
        await http.get("/.well-known/oauth-protected-resource/mcp")
        await http.get("/sante")
        await http.get("/")
    initialisation, ressource, decouverte = (r.getMessage() for r in caplog.records if r.name == "honear_mcp.journal")
    for attendu in (
        "http='POST' chemin='/mcp' code='200' mcp='initialize' outil='-' ressource='-' client='essai/0'",
        "capacites='extensions(io.modelcontextprotocol/ui:text/html;profile=mcp-app),sampling' session='non'",
        "logiciel='Claude-User'",
    ):
        assert attendu in initialisation
    assert "ressource='honear://listes'" in ressource
    assert "SECRET1234" not in ressource
    assert "chemin='/.well-known/oauth-protected-resource/mcp' code='404' mcp='-' session='non'" in decouverte
    assert "127.0.0.1" not in initialisation + ressource + decouverte


async def test_le_mcp_refuse_un_autre_nom_ou_une_page_d_ailleurs(http: httpx2.AsyncClient) -> None:
    autre_nom = await http.post("/mcp", json=INITIALISATION, headers={**EN_TETES_MCP, "Host": "honear.example"})
    ailleurs = await http.post("/mcp", json=INITIALISATION, headers={**EN_TETES_MCP, "Origin": "https://ailleurs.example"})
    assert autre_nom.status_code == 421
    assert ailleurs.status_code == 403


async def test_honear_lit_une_liste_par_le_port_interne_et_la_fait_revivre(rangement: Rangement, horloge: FausseHorloge) -> None:
    pistes = [PisteDeLaListe(deezer=n, titre="T", artiste="A", rang=n, surnoms=Surnoms(), anecdote="") for n in range(5)]
    liste = rangement.creer("Soirée", pistes, dans_l_ordre=True)
    transport = httpx2.ASGITransport(app=application_interne(rangement))
    async with httpx2.AsyncClient(transport=transport, base_url="http://honear-mcp:8791") as http:
        horloge.heure += LISTES.vie - 1
        lue = await http.get(f"/listes/{liste.id}")
        inconnue = await http.get("/listes/inconnue")
        intruse = await http.get("/listes/..%2Flistes")
    assert lue.status_code == 200
    assert Liste.model_validate_json(lue.content).jusqua == liste.jusqua + LISTES.vie - 1
    assert (inconnue.status_code, intruse.status_code) == (404, 404)


async def test_la_page_d_accueil_se_lit_sans_script_sous_une_politique_stricte(http: httpx2.AsyncClient) -> None:
    reponse = await http.get("/")
    assert reponse.status_code == 200
    assert "https://mcp.honear.fr/mcp" in reponse.text
    assert "<script" not in reponse.text
    csp = reponse.headers["content-security-policy"]
    assert csp.startswith("default-src 'none'; style-src 'sha256-")
    assert "frame-ancestors 'none'" in csp


async def test_une_adresse_qui_insiste_trop_attend_son_tour(http: httpx2.AsyncClient, horloge: FausseHorloge) -> None:
    for _ in range(SERVEUR.requetes_par_adresse):
        assert (await http.post("/mcp", json=INITIALISATION, headers=EN_TETES_MCP)).status_code == 200
    de_trop = await http.post("/mcp", json=INITIALISATION, headers=EN_TETES_MCP)
    assert de_trop.status_code == 429
    assert de_trop.headers["retry-after"] == str(round(SERVEUR.fenetre_par_adresse))
    # /sante et l'accueil ne comptent pas ; la fenêtre passée, l'adresse est oubliée.
    assert (await http.get("/sante")).status_code == 200
    horloge.heure += SERVEUR.fenetre_par_adresse
    assert (await http.post("/mcp", json=INITIALISATION, headers=EN_TETES_MCP)).status_code == 200


async def test_les_polices_de_honear_se_servent_a_toute_page_et_rien_d_autre(http: httpx2.AsyncClient) -> None:
    police = await http.get("/polices/caprasimo-400.woff2")
    assert police.status_code == 200
    assert police.headers["content-type"] == "font/woff2"
    assert police.headers["access-control-allow-origin"] == "*"
    assert (await http.get("/polices/LICENCES.md")).status_code == 404
