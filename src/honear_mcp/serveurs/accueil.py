"""La page d'accueil de mcp.honear.fr, pour qui ouvre l'adresse dans un navigateur : ce qu'est le serveur, comment l'ajouter à
son assistant, ce qu'il garde.

La page est une ressource (`ressources/accueil.html`), servie telle quelle, sans script, sous une politique de sécurité du
contenu qui ne laisse passer que sa feuille de style, reconnue à son empreinte.
"""

import base64
import hashlib
import re
from importlib import resources

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from honear_mcp.ressources.reglages import ACCUEIL

_STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)


def page_d_accueil() -> Route:
    """La route `/`, et sa page lue une fois pour toutes."""
    page = resources.files("honear_mcp.ressources").joinpath(ACCUEIL.page).read_text(encoding="utf-8")
    style = _STYLE.search(page)
    empreinte = base64.b64encode(hashlib.sha256((style.group(1) if style else "").encode()).digest()).decode()
    entetes = {"Content-Security-Policy": ACCUEIL.csp.format(style=f"sha256-{empreinte}")}

    async def accueil(_: Request) -> HTMLResponse:
        return HTMLResponse(page, headers=entetes)

    return Route("/", accueil, methods=["GET"])
