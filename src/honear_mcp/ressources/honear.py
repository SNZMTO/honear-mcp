"""Ce que le MCP reprend de Honear, tel que Honear le dit : écrit par `npm run exporter-pour-le-mcp` dans Honear.

Ne pas retoucher : relancer le script, qui écrit aussi tests/jugement-de-honear.json.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JugementDeHonear:
    """Les réglages du jugement d'une saisie (`JUGEMENT`, dans src/ressources/reglages.ts de Honear)."""

    lettres_par_faute: int
    lettres_par_faute_a_l_oreille: int
    presque: float
    morceau: float
    morceau_au_moins: int
    mots_au_plus: int
    saisie_au_plus: int
    articles: tuple[str, ...]
    liaisons: tuple[str, ...]


JUGEMENT = JugementDeHonear(
    lettres_par_faute=4,
    lettres_par_faute_a_l_oreille=5,
    presque=0.4,
    morceau=0.5,
    morceau_au_moins=3,
    mots_au_plus=8,
    saisie_au_plus=120,
    articles=("le", "la", "les", "l", "un", "une", "des", "the", "a", "an"),
    liaisons=("feat", "ft", "featuring", "avec", "x"),
)


@dataclass(frozen=True)
class DeezerDeHonear:
    """La part de Deezer que le jeu prend (`RESEAU.deezer`, dans src/ressources/reseau.ts de Honear)."""

    fenetre: float
    par_fenetre: int


DEEZER_DE_HONEAR = DeezerDeHonear(fenetre=5, par_fenetre=30)


@dataclass(frozen=True)
class PartieDeHonear:
    """Une partie de Honear (`REGLAGES.pistes`, dans src/ressources/reglages.ts de Honear)."""

    pistes_au_moins: int
    """Le moins de pistes jouables qu'une playlist doit avoir : la plus courte des faces qu'on peut choisir. En dessous, le
    bac dit « Trop court pour une face. »"""


PARTIE_DE_HONEAR = PartieDeHonear(pistes_au_moins=10)

PALETTE: dict[str, str] = {
    "noyerSombre": "#4F2E19",
    "noyer": "#734929",
    "noyerClair": "#A8703F",
    "laque": "#1F3A33",
    "vinyle": "#1C1715",
    "alu": "#B8AE9D",
    "miel": "#E2A72E",
    "creme": "#F1E0BD",
    "expresso": "#2A1E17",
    "kraft": "#CBA772",
    "orangeBrule": "#D8652C",
    "rougeTomate": "#C4432F",
    "vieuxRose": "#D08A8F",
    "bleuPetrole": "#1E6E78",
    "bleuFane": "#7FB3C4",
    "olive": "#7E8B3D",
    "lilasFume": "#8C7BB0",
}
"""La palette de Honear (src/ressources/palette.ts), couleur par couleur."""
