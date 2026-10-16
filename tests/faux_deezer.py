"""Le faux Deezer : il rejoue des réponses enregistrées chez le vrai, et échoue sur toute adresse qu'il ne connaît pas.

Les enregistrements sont dans `tests/deezer/`, un fichier par adresse : `{"adresse": …, "reponse": …}`. Un test peut aussi lui
faire refuser les prochains appels (« trop d'appels », comme le vrai), le rendre muet, ou le retenir le temps de compter ceux qui
attendent.
"""

import json
from pathlib import Path

import anyio
import httpx2

from honear_mcp.ressources.deezer import API_DE_DEEZER

ENREGISTREMENTS = Path(__file__).parent / "deezer"
QUOTA = {"error": {"type": "Exception", "message": "Quota limit exceeded", "code": API_DE_DEEZER.quota}}


class FauxDeezer:
    """Un Deezer qui répond de ses enregistrements, et note chaque adresse qu'on lui demande."""

    def __init__(self) -> None:
        self.reponses: dict[str, bytes] = {}
        for fichier in sorted(ENREGISTREMENTS.glob("*.json")):
            enregistrement = json.loads(fichier.read_text(encoding="utf-8"))
            self.reponses[enregistrement["adresse"]] = json.dumps(enregistrement["reponse"]).encode()
        self.appels: list[str] = []
        self.refus_a_venir = 0
        self.muet = False
        self.retenu: anyio.Event | None = None
        self.transport = httpx2.MockTransport(self._repondre)

    async def _repondre(self, requete: httpx2.Request) -> httpx2.Response:
        adresse = str(requete.url).removeprefix(API_DE_DEEZER.adresse)
        self.appels.append(adresse)
        if self.retenu is not None:
            await self.retenu.wait()
        if self.muet:
            raise httpx2.ConnectTimeout("Deezer ne répond pas", request=requete)
        if self.refus_a_venir > 0:
            self.refus_a_venir -= 1
            return httpx2.Response(200, json=QUOTA)
        if adresse not in self.reponses:
            raise AssertionError(f"le faux Deezer n'a rien d'enregistré pour {adresse}")
        return httpx2.Response(200, content=self.reponses[adresse], headers={"content-type": "application/json"})
