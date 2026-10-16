"""Ce que les tests partagent : la boucle asynchrone, le réseau coupé, le faux Deezer, et un client MCP branché au serveur."""

import socket
from collections.abc import AsyncIterator
from pathlib import Path

import httpx2
import pytest
from mcp import Client

from honear_mcp.reseau.deezer import Deezer
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.serveurs.public import creer_le_serveur
from tests.fausse_horloge import FausseHorloge
from tests.faux_deezer import FauxDeezer


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def reseau_coupe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucun test ne sort de la machine : toute connexion échoue, et le dit."""

    def refuser(*_: object) -> None:
        raise AssertionError("un test a voulu se connecter au réseau")

    monkeypatch.setattr(socket.socket, "connect", refuser)
    monkeypatch.setattr(socket.socket, "connect_ex", refuser)
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
