"""Le mini blind test dans la conversation (MCP Apps) : `jouer_ici`, que le modèle appelle, et les trois outils de la fenêtre.

Le modèle ouvre la partie ; il n'en voit ni les titres ni les réponses. La fenêtre écoute la piste en cours (`mini_piste`),
fait juger ce qu'on tape (`mini_repondre`), puis révèle (`mini_reveler`) : ces outils ne sont visibles que de la fenêtre
(`visibility: ["app"]`), et refusent un client qui ne sait pas en afficher une. Un client sans fenêtre reçoit, à la place
d'une partie, le lien pour jouer sur honear.fr.
"""

from typing import Annotated, Literal

from mcp.server.apps import Apps, ResourceCsp
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field, StringConstraints

from honear_mcp.outils.mini_blind_test import Jugee, MiniBlindTest, PartiePrete, PisteAEcouter, Revelee
from honear_mcp.regles.titres import TitreCherche
from honear_mcp.ressources.honear import JUGEMENT
from honear_mcp.ressources.reglages import TITRES
from honear_mcp.ressources.reglages_du_mini import MINI
from honear_mcp.ressources.textes_du_mini import TEXTES_DU_MINI as T

DE_LA_FENETRE: list[Literal["model", "app"]] = ["app"]


def ajouter_le_mini(apps: Apps, mini: MiniBlindTest, page: str) -> None:
    """Ajoute la fenêtre et ses outils à l'extension MCP Apps du serveur."""
    apps.add_html_resource(MINI.fenetre, page, title=T.fenetre, csp=ResourceCsp(resource_domains=list(MINI.domaines)))
    description = T.jouer_ici.description.format(au_moins=MINI.pistes_au_moins, au_plus=MINI.pistes_au_plus, defaut=MINI.pistes)

    @apps.tool(
        resource_uri=MINI.fenetre,
        name="jouer_ici",
        title=T.jouer_ici.titre,
        description=description,
        annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True),
    )
    async def jouer_ici(
        ctx: Context,
        liste: str | None = None,
        titres: Annotated[list[TitreCherche], Field(max_length=TITRES.au_plus)] | None = None,
        pistes: Annotated[int, Field(ge=MINI.pistes_au_moins, le=MINI.pistes_au_plus)] = MINI.pistes,
    ) -> PartiePrete:
        return await mini.ouvrir(ctx, liste, titres, pistes)

    @apps.tool(
        resource_uri=MINI.fenetre,
        visibility=DE_LA_FENETRE,
        name="mini_piste",
        title=T.piste.titre,
        description=T.piste.description,
    )
    async def mini_piste(partie: str, ctx: Context) -> PisteAEcouter:
        return await mini.piste(partie, ctx)

    @apps.tool(
        resource_uri=MINI.fenetre,
        visibility=DE_LA_FENETRE,
        name="mini_repondre",
        title=T.repondre.titre,
        description=T.repondre.description,
    )
    async def mini_repondre(
        partie: str, saisie: Annotated[str, StringConstraints(max_length=JUGEMENT.saisie_au_plus)], ctx: Context
    ) -> Jugee:
        return await mini.repondre(partie, saisie, ctx)

    @apps.tool(
        resource_uri=MINI.fenetre,
        visibility=DE_LA_FENETRE,
        name="mini_reveler",
        title=T.reveler.titre,
        description=T.reveler.description,
    )
    async def mini_reveler(partie: str, ctx: Context) -> Revelee:
        return await mini.reveler(partie, ctx)
