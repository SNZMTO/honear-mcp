"""Les prompts prêts : une soirée, un thème, une playlist d'ailleurs. Chacun dit au modèle quoi choisir, et quoi en faire."""

from mcp.server.mcpserver import MCPServer

from honear_mcp.ressources.reglages import LISTES
from honear_mcp.ressources.textes import TEXTES


def ajouter_les_prompts(serveur: MCPServer) -> None:
    """Ajoute les trois prompts au serveur."""

    @serveur.prompt(name="soiree", title=TEXTES.soiree.titre, description=TEXTES.soiree.description)
    def soiree(occasion: str, invites: str, nombre: int = LISTES.proposees) -> str:
        return TEXTES.soiree.message.format(occasion=occasion, invites=invites, nombre=nombre)

    @serveur.prompt(name="theme", title=TEXTES.theme.titre, description=TEXTES.theme.description)
    def theme(theme: str, nombre: int = LISTES.proposees) -> str:
        return TEXTES.theme.message.format(theme=theme, nombre=nombre)

    @serveur.prompt(name="importer", title=TEXTES.importer.titre, description=TEXTES.importer.description)
    def importer(source: str) -> str:
        return TEXTES.importer.message.format(source=source)
