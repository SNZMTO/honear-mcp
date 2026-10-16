"""L'appel à Deezer : sous la limite de débit du MCP, avec un temps pour répondre, quelques essais quand il dit qu'on va trop
vite, et les recherches gardées un moment.

Un seul `Deezer` sert tous les outils et toutes les sessions : sa limite vaut pour tout le serveur, quel que soit le nombre de
clients branchés. Un appel qui ne peut pas aboutir le dit par `DeezerIndisponible`.
"""

import httpx2

from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.debit import Fenetre
from honear_mcp.reseau.horloge import Horloge
from honear_mcp.ressources.deezer import API_DE_DEEZER
from honear_mcp.ressources.reglages import DEEZER
from honear_mcp.ressources.reglages_du_mini import MINI
from honear_mcp.sources.deezer import (
    PisteDeDeezer,
    adresse_de_la_piste,
    adresse_de_recherche,
    expiration_de,
    lire_la_piste,
    lire_les_pistes,
    refus_de,
)


class DeezerIndisponible(Exception):
    """Deezer n'a pas répondu à temps, a refusé, ou trop d'appels attendent déjà leur tour : on réessaiera plus tard."""


class Deezer:
    """Le Deezer du serveur : sa limite de débit, ses appels en attente, les réponses qu'il garde."""

    def __init__(self, client: httpx2.AsyncClient, horloge: Horloge) -> None:
        """Un Deezer qui appelle par `client` (son temps de réponse y est réglé) et lit l'heure sur `horloge`."""
        self._client = client
        self._horloge = horloge
        self._fenetre = Fenetre(DEEZER.par_fenetre, DEEZER.fenetre, horloge)
        self._gardees: dict[str, tuple[float, bytes]] = {}
        self._vues: dict[int, tuple[float, PisteDeDeezer]] = {}
        self._en_attente = 0

    @property
    def en_attente(self) -> int:
        """Combien d'appels attendent leur tour ou leur réponse."""
        return self._en_attente

    @property
    def gardees(self) -> int:
        """Combien de réponses sont gardées, fraîches ou pas encore oubliées."""
        return len(self._gardees)

    async def chercher(self, cherche: TitreCherche) -> list[PisteDeDeezer]:
        """Les pistes que Deezer trouve pour un titre, dans son ordre. On se souvient un moment de chacune."""
        pistes = lire_les_pistes(await self._lire(adresse_de_recherche(cherche.artiste, cherche.titre)))
        self._voir(pistes)
        return pistes

    async def piste(self, deezer: int) -> PisteDeDeezer | None:
        """La piste de cet identifiant : celle qu'une recherche récente a vue, ou sa fiche chez Deezer ; rien s'il n'en a pas."""
        vue = self._vues.get(deezer)
        if vue is not None and vue[0] > self._horloge.maintenant():
            return vue[1]
        return lire_la_piste(await self._lire(adresse_de_la_piste(deezer)))

    async def a_ecouter(self, deezer: int) -> PisteDeDeezer | None:
        """La piste de cet identifiant, avec un extrait qu'on aura le temps d'écouter : celle qu'on a vue, si son lien n'expire
        pas avant tant de minutes, sinon sa fiche relue chez Deezer ; rien si elle n'a plus d'extrait."""
        avant = self._horloge.monde() + MINI.marge_de_l_extrait
        vue = await self.piste(deezer)
        if vue is not None and vue.preview and (expiration_de(vue.preview) or avant) >= avant:
            return vue
        relue = lire_la_piste(await self._lire(adresse_de_la_piste(deezer), frais=True))
        if relue is not None:
            self._voir([relue])
        return relue if relue is not None and relue.preview else None

    async def _lire(self, adresse: str, *, frais: bool = False) -> bytes:
        """La réponse à cette adresse : celle qu'on garde, si elle est encore bonne et qu'on n'en veut pas une fraîche."""
        gardee = self._gardees.get(adresse)
        if not frais and gardee is not None and gardee[0] > self._horloge.maintenant():
            return gardee[1]
        if self._en_attente >= DEEZER.file_au_plus:
            raise DeezerIndisponible
        self._en_attente += 1
        try:
            corps = await self._appeler(adresse)
        finally:
            self._en_attente -= 1
        self._garder(adresse, corps)
        return corps

    async def _appeler(self, adresse: str) -> bytes:
        """La réponse de Deezer, ou ce qu'il dit quand il n'y a rien à cette adresse ; quand il dit qu'on va trop vite, on attend
        une fenêtre et on redemande, tant de fois au plus."""
        for essai in range(DEEZER.essais):
            if essai > 0:
                await self._horloge.attendre(DEEZER.fenetre)
            await self._fenetre.son_tour()
            try:
                reponse = await self._client.get(f"{API_DE_DEEZER.adresse}{adresse}")
            except httpx2.HTTPError as erreur:
                raise DeezerIndisponible from erreur
            refus = refus_de(reponse.content) if reponse.is_success else "autre"
            if refus is None or refus == "introuvable":
                return reponse.content
            if refus == "autre":
                raise DeezerIndisponible
        raise DeezerIndisponible

    def _voir(self, pistes: list[PisteDeDeezer]) -> None:
        """Se souvient des pistes d'une recherche, le temps qu'on garde une recherche, et de tant au plus."""
        jusqua = self._horloge.maintenant() + DEEZER.recherche_gardee
        for piste in pistes:
            self._vues.pop(piste.id, None)
            self._vues[piste.id] = (jusqua, piste)
        while len(self._vues) > DEEZER.vues_au_plus:
            del self._vues[next(iter(self._vues))]

    def _garder(self, adresse: str, corps: bytes) -> None:
        """Garde une réponse : on oublie d'abord celles qui ont fait leur temps, puis les plus anciennes, s'il le faut."""
        maintenant = self._horloge.maintenant()
        for vieille in [a for a, (jusqua, _) in self._gardees.items() if jusqua <= maintenant]:
            del self._gardees[vieille]
        self._gardees.pop(adresse, None)
        while len(self._gardees) >= DEEZER.gardees_au_plus:
            del self._gardees[next(iter(self._gardees))]
        self._gardees[adresse] = (maintenant + DEEZER.recherche_gardee, corps)
