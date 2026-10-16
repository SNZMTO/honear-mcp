"""Le mini blind test dans la conversation : une partie, ses pistes, ce qu'on a trouvé de celle qu'on écoute, et les points.

On y juge comme en saisie libre dans Honear : l'artiste et le titre se trouvent l'un après l'autre ou d'un coup, aux fautes
près, avec les surnoms d'une liste, et chacun vaut un point. La réponse d'une piste ne sort de la partie qu'à sa révélation.
"""

from pydantic import BaseModel, ConfigDict

from honear_mcp.regles.jugement import Verdict
from honear_mcp.regles.liste import Surnoms
from honear_mcp.regles.parties import Partie, cibles_de, juger_les_parties


class PisteDuMini(BaseModel):
    """Une piste à faire deviner, et ce qu'on montre à sa révélation."""

    model_config = ConfigDict(frozen=True)

    deezer: int
    titre: str
    artiste: str
    surnoms: Surnoms = Surnoms()
    anecdote: str = ""


class PartieDuMini(BaseModel):
    """Une partie : ses pistes dans l'ordre où elles se jouent, la piste en cours, ce qu'on en a trouvé, les points."""

    model_config = ConfigDict(frozen=True)

    nom: str
    pistes: list[PisteDuMini]
    rang: int = 0
    trouvees: list[Partie] = []
    points: int = 0

    @property
    def finie(self) -> bool:
        """Vrai quand toutes les pistes ont été révélées."""
        return self.rang >= len(self.pistes)


A_TROUVER: list[Partie] = ["artiste", "titre"]
"""Ce qu'on trouve d'une piste : son artiste et son titre (une recherche ne dit pas ses invités)."""


def juger_la_saisie(partie: PartieDuMini, saisie: str) -> tuple[PartieDuMini, Verdict]:
    """La partie après une saisie sur la piste en cours, et le verdict de cette saisie."""
    piste = partie.pistes[partie.rang]
    surnoms: dict[Partie, list[str]] = {"artiste": piste.surnoms.artiste, "titre": piste.surnoms.titre}
    cibles = cibles_de(piste.artiste, piste.titre, None, surnoms)
    trouve, verdict = juger_les_parties(saisie, A_TROUVER, cibles, partie.trouvees)
    return partie.model_copy(update={"trouvees": [*partie.trouvees, *trouve], "points": partie.points + len(trouve)}), verdict


def reveler(partie: PartieDuMini) -> tuple[PartieDuMini, PisteDuMini]:
    """La partie passée à la piste suivante, et la piste qu'on vient de révéler."""
    return partie.model_copy(update={"rang": partie.rang + 1, "trouvees": []}), partie.pistes[partie.rang]
