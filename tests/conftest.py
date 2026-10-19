"""Ce que les tests partagent : la boucle asynchrone, le réseau coupé, le faux Deezer, et un client MCP branché au serveur."""

import socket
from collections.abc import AsyncIterator
from pathlib import Path
from typing import NoReturn

import httpx2
import pytest
from mcp import Client

from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.serveurs.public import creer_le_serveur
from tests.fausse_horloge import FausseHorloge
from tests.faux_deezer import FauxDeezer

LA_MACHINE = {"127.0.0.1", "::1"}
"""Les seules adresses qu'un test peut joindre : la machine elle-même, jamais le réseau."""


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def reseau_coupe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucun test ne sort de la machine : toute connexion échoue, et le dit, sauf vers la machine elle-même. Sous Windows, la
    boucle asyncio se parle par une connexion à 127.0.0.1 (le repli de `socket.socketpair`) : sans elle, aucun test asynchrone
    ne démarrerait."""
    connecter, connecter_ex = socket.socket.connect, socket.socket.connect_ex

    def refuser(*_: object) -> NoReturn:
        raise AssertionError("un test a voulu se connecter au réseau")

    def vers_la_machine(sock: socket.socket, adresse: object) -> None:
        if not (isinstance(adresse, tuple) and adresse[0] in LA_MACHINE):
            refuser()
        connecter(sock, adresse)

    def vers_la_machine_ex(sock: socket.socket, adresse: object) -> int:
        if not (isinstance(adresse, tuple) and adresse[0] in LA_MACHINE):
            refuser()
        return connecter_ex(sock, adresse)

    monkeypatch.setattr(socket.socket, "connect", vers_la_machine)
    monkeypatch.setattr(socket.socket, "connect_ex", vers_la_machine_ex)
    monkeypatch.setattr(socket, "getaddrinfo", refuser)


@pytest.fixture
def faux_deezer() -> FauxDeezer:
    return FauxDeezer()


@pytest.fixture
def horloge() -> FausseHorloge:
    return FausseHorloge()


@pytest.fixture
async def deezer(faux_deezer: FauxDeezer, horloge: FausseHorloge) -> AsyncIterator[Deezer]:
    async with httpx2.AsyncClient(transport=faux_deezer.transport) as client:
        yield Deezer(client, horloge)


@pytest.fixture
def rangement(tmp_path: Path, horloge: FausseHorloge) -> Rangement:
    return Rangement(tmp_path / "listes", horloge)


@pytest.fixture
def parties(horloge: FausseHorloge) -> Parties:
    return Parties(horloge)


@pytest.fixture
async def client(deezer: Deezer, rangement: Rangement, parties: Parties) -> AsyncIterator[Client]:
    """Un client MCP branché en mémoire au serveur public : le chemin d'un vrai client, sans HTTP."""
    async with Client(creer_le_serveur(deezer, rangement, parties), raise_exceptions=True) as client:
        yield client
