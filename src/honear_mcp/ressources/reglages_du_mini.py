"""Les réglages du mini blind test dans la conversation : ses parties, ses extraits, et ce que sa fenêtre peut charger."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReglagesDuMini:
    """Le mini blind test dans la conversation : ses parties, en mémoire, et sa fenêtre (MCP Apps).

    Une partie vit une heure après son dernier geste, 200 au plus à la fois. Un extrait se relit chez Deezer s'il expire dans
    moins de deux minutes : de quoi l'écouter jusqu'au bout. La fenêtre ne charge rien d'autre que les polices du MCP, les
    extraits et les pochettes de Deezer.
    """

    pistes: int
    """Combien de pistes une partie joue, si on ne dit rien."""
    pistes_au_moins: int
    pistes_au_plus: int
    parties_au_plus: int
    vie: float
    marge_de_l_extrait: float
    fenetre: str
    """L'adresse de la fenêtre, une ressource `ui://`."""
    domaines: tuple[str, ...]
    """Ce que la fenêtre peut charger : les polices du MCP, les extraits et les pochettes de Deezer."""
    site: str
    """L'adresse publique du MCP, d'où la fenêtre charge ses polices."""
    polices: tuple[str, ...]


MINI = ReglagesDuMini(
    pistes=5,
    pistes_au_moins=3,
    pistes_au_plus=10,
    parties_au_plus=200,
    vie=3600,
    marge_de_l_extrait=120,
    fenetre="ui://honear/mini-blind-test.html",
    domaines=("https://mcp.honear.fr", "https://*.dzcdn.net"),
    site="https://mcp.honear.fr",
    polices=("caprasimo-400.woff2", "barlow-condensed-500.woff2", "barlow-condensed-600.woff2"),
)
