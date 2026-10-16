"""Ce que font les outils du mini blind test, sur les parties en mémoire : ouvrir, faire écouter, juger, révéler.

Les outils (`outils/mini.py`) n'en sont que l'entrée ; c'est ici qu'on refuse ce qui ne va pas, avec une phrase à lire.
"""

from mcp.server.apps import client_supports_apps
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

from honear_mcp.regles.liste import Liste
from honear_mcp.regles.mini import PartieDuMini, PisteDuMini, juger_la_saisie, reveler
from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.deezer import Deezer, DeezerIndisponible
from honear_mcp.reseau.hasard import melanger
from honear_mcp.reseau.parties import Parties
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages import HONEAR
from honear_mcp.ressources.reglages_du_mini import MINI
from honear_mcp.ressources.textes_du_mini import TEXTES_DU_MINI as T
from honear_mcp.sources.correspondance import Trouve, resultat_de
from honear_mcp.sources.deezer import pochette_de


class PartiePrete(BaseModel):
    """Ce que le modèle apprend d'une partie : rien de ses pistes. La fenêtre y lit son identifiant."""

    partie: str
    """L'identifiant de la partie, que la fenêtre passe à ses outils."""
    nom: str
    total: int
    message: str


class PisteAEcouter(BaseModel):
    """La piste en cours, sans sa réponse : son rang, et son extrait."""

    rang: int
    total: int
    extrait: str


class Jugee(BaseModel):
    """Ce qu'une saisie a trouvé de la piste en cours, son verdict, et les points de la partie."""

    trouve: list[str]
    verdict: str
    points: int


class Revelee(BaseModel):
    """La piste révélée : sa réponse, son anecdote, sa pochette, ce qu'on en avait trouvé, et où en est la partie."""

    rang: int
    total: int
    titre: str
    artiste: str
    anecdote: str
    pochette: str | None
    trouve: list[str]
    points: int
    finie: bool


class MiniBlindTest:
    """Les parties du mini blind test, et Deezer pour leurs extraits et leurs pochettes."""

    def __init__(self, deezer: Deezer, rangement: Rangement, parties: Parties) -> None:
        """Le mini blind test cherche par `deezer`, lit les listes dans `rangement`, tient ses parties dans `parties`."""
        self._deezer = deezer
        self._rangement = rangement
        self._parties = parties

    async def ouvrir(self, ctx: Context, liste: str | None, titres: list[TitreCherche] | None, pistes: int) -> PartiePrete:
        """Une partie neuve, d'une liste ou de titres. Elle s'ouvre même quand l'appel ne dit pas que le client sait montrer la
        fenêtre : claude.ai la montre, sans le dire dans l'appel de l'outil (c'est la fenêtre, ensuite, qui le dit). Le message
        donne alors aussi le lien pour jouer sur honear.fr, si elle ne s'affiche pas."""
        if (liste is None) == (titres is None):
            raise ToolError(T.une_seule_source)
        lue = self._rangement.lire(liste) if liste is not None else None
        if liste is not None and lue is None:
            raise ToolError(T.inconnue)
        nom = lue.nom if lue is not None else T.nom
        choisies = self._de_la_liste(lue) if lue is not None else await self._des_titres(titres or [])
        if len(choisies) < MINI.pistes_au_moins:
            raise ToolError(T.trop_peu.format(n=len(choisies), au_moins=MINI.pistes_au_moins))
        partie = PartieDuMini(nom=nom, pistes=choisies[:pistes])
        id_de_partie = self._parties.ouvrir(partie)
        if id_de_partie is None:
            raise ToolError(T.pleines)
        if liste is not None:
            self._rangement.jouee(liste)
        total = len(partie.pistes)
        message = T.prete.format(nom=nom, total=total)
        if not client_supports_apps(ctx):
            ailleurs = T.sans_fenetre_liste.format(lien=HONEAR.lien_de_liste.format(id=liste)) if liste else T.sans_fenetre_titres
            message = f"{message} {ailleurs}"
        return PartiePrete(partie=id_de_partie, nom=nom, total=total, message=message)

    async def piste(self, id_de_partie: str, ctx: Context) -> PisteAEcouter:
        """L'extrait de la piste en cours, relu chez Deezer s'il allait expirer."""
        partie = self._en_cours(id_de_partie, ctx)
        try:
            piste = await self._deezer.a_ecouter(partie.pistes[partie.rang].deezer)
        except DeezerIndisponible as erreur:
            raise ToolError(T.sans_extrait) from erreur
        if piste is None:
            raise ToolError(T.sans_extrait)
        return PisteAEcouter(rang=partie.rang + 1, total=len(partie.pistes), extrait=piste.preview)

    def repondre(self, id_de_partie: str, saisie: str, ctx: Context) -> Jugee:
        """Une saisie jugée sur la piste en cours, comme dans Honear."""
        jugee, verdict = juger_la_saisie(self._en_cours(id_de_partie, ctx), saisie)
        self._parties.garder(id_de_partie, jugee)
        return Jugee(trouve=list(jugee.trouvees), verdict=verdict, points=jugee.points)

    async def reveler(self, id_de_partie: str, ctx: Context) -> Revelee:
        """La réponse de la piste en cours ; la partie passe à la suivante."""
        partie = self._en_cours(id_de_partie, ctx)
        suivante, piste = reveler(partie)
        self._parties.garder(id_de_partie, suivante)
        try:
            vue = await self._deezer.piste(piste.deezer)
        except DeezerIndisponible:
            vue = None
        return Revelee(
            rang=partie.rang + 1,
            total=len(partie.pistes),
            titre=piste.titre,
            artiste=piste.artiste,
            anecdote=piste.anecdote,
            pochette=pochette_de(vue) if vue is not None else None,
            trouve=list(partie.trouvees),
            points=suivante.points,
            finie=suivante.finie,
        )

    def _en_cours(self, id_de_partie: str, ctx: Context) -> PartieDuMini:
        """La partie, si c'est bien la fenêtre qui la demande (son client dit qu'il sait la montrer) et qu'il lui reste une
        piste."""
        if not client_supports_apps(ctx):
            raise ToolError(T.reservee)
        partie = self._parties.lire(id_de_partie)
        if partie is None or partie.finie:
            raise ToolError(T.inconnue)
        return partie

    @staticmethod
    def _de_la_liste(liste: Liste) -> list[PisteDuMini]:
        champs = {"deezer", "titre", "artiste", "surnoms", "anecdote"}
        pistes = [PisteDuMini.model_validate(p.model_dump(include=champs)) for p in liste.pistes]
        return pistes if liste.dans_l_ordre else [pistes[rang] for rang in melanger(len(pistes))]

    async def _des_titres(self, titres: list[TitreCherche]) -> list[PisteDuMini]:
        pistes = []
        for cherche in titres:
            try:
                resultat = resultat_de(cherche, await self._deezer.chercher(cherche))
            except DeezerIndisponible:
                continue
            if isinstance(resultat, Trouve) and "sans_extrait" not in resultat.piste.drapeaux:
                trouvee = resultat.piste
                pistes.append(PisteDuMini(deezer=trouvee.deezer, titre=trouvee.titre, artiste=trouvee.artiste))
        return [pistes[rang] for rang in melanger(len(pistes))]
