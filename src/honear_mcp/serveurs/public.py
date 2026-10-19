"""Le serveur public, celui de https://mcp.honear.fr : ses outils, son entrée MCP (`/mcp`), sa page d'accueil (`/`) et ce qu'il
dit de lui (`/sante`).

À côté, sur un second port que le frontal ne relaie pas, Honear lit les listes (`/listes/<id>`). `uv run honear-mcp` lance les
deux ; un client MCP se branche alors sur http://127.0.0.1:8790/mcp. Deux variables d'environnement changent ce que disent les
réglages : HONEAR_MCP_LISTES, le dossier des listes, et HONEAR_MCP_HOTE, où l'on écoute (0.0.0.0 dans le conteneur).
"""

import math
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from importlib.metadata import version
from pathlib import Path

import anyio
import httpx2
import uvicorn
from mcp.server.apps import Apps
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types.version import HANDSHAKE_PROTOCOL_VERSIONS
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from honear_mcp.outils.listes import ajouter_les_listes
from honear_mcp.outils.mini import ajouter_le_mini
from honear_mcp.outils.mini_blind_test import MiniBlindTest
from honear_mcp.outils.prompts import ajouter_les_prompts
from honear_mcp.outils.titres import ajouter_chercher_titres
from honear_mcp.reseau.debit import ParAdresse
from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.horloge import Horloge, HorlogeDuSysteme
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages import DEEZER, LISTES, SERVEUR
from honear_mcp.ressources.textes import TEXTES
from honear_mcp.serveurs.accueil import page_d_accueil
from honear_mcp.serveurs.fenetre import page_du_mini, polices
from honear_mcp.serveurs.journal import journaliser, regler_les_journaux


def creer_le_serveur(deezer: Deezer, rangement: Rangement, parties: Parties) -> MCPServer:
    """Le serveur MCP, ses outils, ses ressources, ses prompts et la fenêtre du mini blind test (l'extension MCP Apps) : ils
    cherchent tous par le même `deezer`."""
    apps = Apps()
    ajouter_le_mini(apps, MiniBlindTest(deezer, rangement, parties), page_du_mini())
    serveur = MCPServer(
        name="honear",
        title="Honear",
        version=version("honear-mcp"),
        instructions=TEXTES.instructions,
        website_url="https://honear.fr",
        extensions=[apps],
    )
    ajouter_chercher_titres(serveur, deezer)
    ajouter_les_listes(serveur, deezer, rangement)
    ajouter_les_prompts(serveur)
    return serveur


def _ouvre_une_session(scope: Scope) -> bool:
    """Vrai pour une requête qui peut ouvrir une session : un POST sans session, de l'ancien protocole (sans version, ou d'une
    version qui passe par `initialize`). On ne lit que ses en-têtes : le protocole 2026-07-28, qui n'a pas de session, et les
    requêtes d'une session ouverte n'y comptent pas."""
    entetes = Headers(scope=scope)
    version_demandee = entetes.get("mcp-protocol-version")
    ancienne = version_demandee is None or version_demandee in HANDSHAKE_PROTOCOL_VERSIONS
    return scope["method"] == "POST" and "mcp-session-id" not in entetes and ancienne


def _par_adresse(app: ASGIApp, limite: ParAdresse, sessions: ParAdresse) -> ASGIApp:
    """Le MCP derrière les limites de chaque adresse, ses requêtes et les sessions qu'elle ouvre : au-delà, une réponse 429 qui
    dit dans combien de secondes revenir.

    L'adresse est celle du client, que le frontal donne (uvicorn lit son en-tête X-Forwarded-For) ; elle ne sert qu'à compter.
    """

    async def garde(scope: Scope, receive: Receive, send: Send) -> None:
        client = scope.get("client")
        if scope["type"] == "http" and client is not None:
            adresse = str(client[0])
            attente = limite.attente(adresse)
            if not _ouvre_une_session(scope):
                sessions.menage()
            elif attente == 0:
                attente = sessions.attente(adresse)
            if attente > 0:
                refus = Response(status_code=HTTPStatus.TOO_MANY_REQUESTS, headers={"Retry-After": str(math.ceil(attente))})
                await refus(scope, receive, send)
                return
        await app(scope, receive, send)

    return garde


def application(deezer: Deezer, rangement: Rangement, parties: Parties, horloge: Horloge) -> Starlette:
    """L'application web : la page d'accueil, `/sante`, puis le MCP pour tout le reste.

    Le MCP ne répond qu'aux noms et aux pages qu'on lui nomme (contre le DNS rebinding), compte les requêtes de chaque adresse
    et les sessions qu'elle ouvre, borne les sessions des anciens clients, et laisse une ligne au journal par requête, sans
    adresse (`journal.py`). Son gestionnaire de sessions vit le temps de l'application : c'est elle qui le démarre.
    """
    serveur = creer_le_serveur(deezer, rangement, parties)
    mcp = serveur.streamable_http_app(
        transport_security=TransportSecuritySettings(allowed_hosts=list(SERVEUR.hotes), allowed_origins=list(SERVEUR.origines)),
        session_idle_timeout=SERVEUR.session_oubliee,
        max_sessions=SERVEUR.sessions_au_plus,
    )

    async def sante(_: Request) -> JSONResponse:
        """Ce que le serveur dit de lui-même : de quoi vérifier une mise en ligne d'un coup d'œil, et voir s'il est occupé."""
        etat = {"deezer_en_attente": deezer.en_attente, "recherches_gardees": deezer.gardees, "listes": rangement.nombre()}
        return JSONResponse({**etat, "parties": parties.en_cours})

    @asynccontextmanager
    async def cycle(_: Starlette) -> AsyncIterator[None]:
        async with serveur.session_manager.run():
            yield

    limite = ParAdresse(SERVEUR.requetes_par_adresse, SERVEUR.fenetre_par_adresse, SERVEUR.adresses_au_plus, horloge)
    sessions = ParAdresse(SERVEUR.sessions_par_adresse, SERVEUR.fenetre_des_sessions, SERVEUR.adresses_au_plus, horloge)
    routes = [
        page_d_accueil(),
        polices(),
        Route("/sante", sante, methods=["GET"]),
        Mount("/", app=journaliser(_par_adresse(mcp, limite, sessions))),
    ]
    return Starlette(routes=routes, lifespan=cycle)


def application_interne(rangement: Rangement) -> Starlette:
    """Ce que Honear lit, sur le réseau Docker qu'il partage avec le MCP : une liste par son identifiant.

    Lire une liste, c'est la jouer : elle vit de nouveau toute une vie. Une liste inconnue ou oubliée répond 404.
    """

    async def une_liste(requete: Request) -> Response:
        liste = rangement.jouee(str(requete.path_params["id_de_liste"]))
        if liste is None:
            return Response(status_code=HTTPStatus.NOT_FOUND)
        return Response(liste.model_dump_json(), media_type="application/json")

    return Starlette(routes=[Route("/listes/{id_de_liste}", une_liste, methods=["GET"])])


async def _servir() -> None:
    # Ni le journal des requêtes d'uvicorn, qui garderait l'adresse IP de chaque client (le nôtre, `journal.py`, ne la lit pas),
    # ni ceux des appels à Deezer et du SDK, qui garderaient ce que les gens cherchent, leurs listes et leurs sessions.
    regler_les_journaux()
    horloge = HorlogeDuSysteme()
    rangement = Rangement(Path(os.environ.get("HONEAR_MCP_LISTES", LISTES.dossier)), horloge)
    rangement.oublier_les_vieilles()
    hote = os.environ.get("HONEAR_MCP_HOTE", SERVEUR.hote)
    async with httpx2.AsyncClient(timeout=DEEZER.attente) as client, anyio.create_task_group() as taches:
        # L'adresse d'un client est celle que donne le frontal : seul lui joint ce port, par son réseau.
        publique = uvicorn.Config(
            application(Deezer(client, horloge), rangement, Parties(horloge), horloge),
            host=hote,
            port=SERVEUR.port,
            access_log=False,
            server_header=False,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
        interne = uvicorn.Config(
            application_interne(rangement), host=hote, port=SERVEUR.port_interne, access_log=False, server_header=False
        )
        for config in (publique, interne):
            taches.start_soon(uvicorn.Server(config).serve)


def lancer() -> None:
    """Le point d'entrée de `honear-mcp` : sert le MCP jusqu'à ce qu'on l'arrête."""
    anyio.run(_servir)
