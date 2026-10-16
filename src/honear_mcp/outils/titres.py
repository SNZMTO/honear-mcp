"""L'outil `chercher_titres` : retrouver chez Deezer les titres que le modèle propose, par lots, et dire ce qui cloche.

C'est le modèle qui choisit les titres (« des chansons avec une couleur dans le titre ») ; l'outil dit lesquels existent, s'ils
ont un extrait, et ce qui les jouerait mal. Il ne change rien : le même lot redonne la même réponse, sans rappeler Deezer
de quelque temps.
"""

from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.deezer import Deezer, DeezerIndisponible
from honear_mcp.ressources.reglages import TITRES
from honear_mcp.ressources.textes import TEXTES
from honear_mcp.sources.correspondance import Resultat, resultat_de, sans_doublons


class Recherche(BaseModel):
    """Ce que Deezer dit de chaque titre demandé, dans l'ordre de la demande."""

    resultats: list[Resultat]


def ajouter_chercher_titres(serveur: MCPServer, deezer: Deezer) -> None:
    """Ajoute l'outil au serveur : il cherche par `deezer`, sous sa limite."""

    @serveur.tool(
        name="chercher_titres",
        title=TEXTES.chercher_titres.titre,
        description=TEXTES.chercher_titres.description.format(au_plus=TITRES.au_plus),
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True),
    )
    async def chercher_titres(
        titres: Annotated[list[TitreCherche], Field(min_length=1, max_length=TITRES.au_plus)], ctx: Context
    ) -> Recherche:
        resultats: list[Resultat] = []
        for cherche in titres:
            try:
                pistes = await deezer.chercher(cherche)
            except DeezerIndisponible as erreur:
                raise ToolError(TEXTES.deezer_indisponible) from erreur
            resultats.append(resultat_de(cherche, pistes))
            await ctx.report_progress(len(resultats), len(titres))
        return Recherche(resultats=sans_doublons(resultats))
