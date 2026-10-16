"""La fenêtre du mini blind test : sa page, assemblée au démarrage, et les polices qu'elle charge depuis mcp.honear.fr.

La page part d'un gabarit (`ressources/mini-blind-test.html`) ; on y pose la palette de Honear, l'adresse de ses polices et le
script que construit `interface/` (`ressources/mini-blind-test.js`). Les polices se servent sur `/polices/<fichier>`, à
n'importe quelle page qui les demande : la fenêtre vit sur le domaine de l'hôte, pas sur le nôtre.
"""

from http import HTTPStatus
from importlib import resources

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from honear_mcp.ressources.honear import PALETTE
from honear_mcp.ressources.reglages_du_mini import MINI

_RESSOURCES = resources.files("honear_mcp.ressources")


def page_du_mini() -> str:
    """La page de la fenêtre, d'un seul tenant : son style, ses couleurs, son script."""
    gabarit = _RESSOURCES.joinpath("mini-blind-test.html").read_text(encoding="utf-8")
    script = _RESSOURCES.joinpath("mini-blind-test.js").read_text(encoding="utf-8")
    couleurs = "\n".join(f"  --{nom}: {couleur};" for nom, couleur in PALETTE.items())
    return gabarit.replace("__COULEURS__", couleurs).replace("__SITE__", MINI.site).replace("__SCRIPT__", script)


def polices() -> Route:
    """La route `/polices/<fichier>` : les polices de Honear, et rien d'autre, gardées un an par qui les lit."""
    contenus = {nom: _RESSOURCES.joinpath("polices", nom).read_bytes() for nom in MINI.polices}
    entetes = {"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=31536000, immutable"}

    async def police(requete: Request) -> Response:
        contenu = contenus.get(str(requete.path_params["fichier"]))
        if contenu is None:
            return Response(status_code=HTTPStatus.NOT_FOUND)
        return Response(contenu, media_type="font/woff2", headers=entetes)

    return Route("/polices/{fichier}", police, methods=["GET"])
