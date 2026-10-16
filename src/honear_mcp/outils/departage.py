"""Départager les titres ambigus d'une liste : demander à l'hôte quand son client le permet, sinon rendre les candidats au modèle.

La question est un formulaire d'élicitation : un choix par titre ambigu (« Bohemian Rapsody » : l'original, le live, ou aucun).
Elle se pose avant que l'outil commence, par un résolveur du SDK : sur un client du protocole 2026-07-28, elle part dans la
réponse et revient avec la suivante, et le résolveur repasse ; les recherches gardées la refont à l'identique.
"""

from collections.abc import Awaitable, Callable

from mcp.server.mcpserver import Context, Elicit
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, JsonValue
from pydantic.config import JsonDict

from honear_mcp.regles.liste import PisteDemandee
from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.deezer import Deezer, DeezerIndisponible
from honear_mcp.ressources.reglages import LISTES
from honear_mcp.ressources.textes import TEXTES
from honear_mcp.sources.correspondance import Ambigu, resultat_de

AUCUN = "aucun"
"""Ce que l'hôte répond pour écarter un titre ambigu."""


class SansQuestion(BaseModel):
    """Ce que le résolveur rend sans rien demander : aucun titre n'est ambigu, ou on ne peut pas les faire départager (trop
    nombreux, ou un client qui ne sait pas demander). L'outil rend alors les candidats au modèle."""


def _champ(rang: int) -> str:
    return f"titre_{rang}"


def choix_de(reponse: BaseModel, rang: int) -> str:
    """Ce que l'hôte a choisi pour le titre de ce rang : un identifiant Deezer, `AUCUN`, ou rien si on ne lui a pas demandé."""
    valeur = reponse.model_dump().get(_champ(rang))
    return valeur if isinstance(valeur, str) else ""


def _sait_demander(ctx: Context) -> bool:
    """Vrai si le client a dit savoir montrer un formulaire (l'élicitation en mode formulaire)."""
    capacites = ctx.client_capabilities
    elicitation = capacites.elicitation if capacites is not None else None
    return elicitation is not None and (elicitation.form is not None or elicitation.url is None)


def _formulaire(ambigus: list[tuple[int, Ambigu]]) -> type[BaseModel]:
    """Le formulaire : pour chaque titre ambigu, un choix parmi ses candidats (par leur identifiant Deezer) et « aucun ».

    Ses champs changent d'une demande à l'autre : le schéma se complète à chaque fois, et la réponse se lit champ par champ.
    """
    proprietes: JsonDict = {}
    for rang, ambigu in ambigus:
        options: list[JsonValue] = [
            {
                "const": str(c.deezer),
                "title": TEXTES.listes.candidat.format(titre=c.titre_complet, artiste=c.artiste, album=c.album),
            }
            for c in ambigu.candidats
        ]
        options.append({"const": AUCUN, "title": TEXTES.listes.aucun})
        proprietes[_champ(rang)] = {
            "type": "string",
            "title": f"{ambigu.cherche.artiste} — {ambigu.cherche.titre}",
            "oneOf": options,
        }

    def completer(schema: JsonDict) -> None:
        schema["properties"] = proprietes
        schema["required"] = list(proprietes)
        schema.pop("additionalProperties", None)

    class Departage(BaseModel):
        model_config = ConfigDict(extra="allow", json_schema_extra=completer)

    return Departage


def refus_des_ambigus(ambigus: list[Ambigu]) -> ToolError:
    """Le refus qui rend au modèle les candidats de chaque titre ambigu, pour qu'il demande lui-même."""
    lignes = [
        TEXTES.listes.ligne_ambigue.format(
            artiste=ambigu.cherche.artiste,
            titre=ambigu.cherche.titre,
            candidats=" ; ".join(
                TEXTES.listes.candidat_ambigu.format(deezer=c.deezer, titre=c.titre_complet, artiste=c.artiste, album=c.album)
                for c in ambigu.candidats
            ),
        )
        for ambigu in ambigus
    ]
    return ToolError(TEXTES.listes.ambigus.format(lignes="\n".join(lignes)))


def resolveur(deezer: Deezer) -> Callable[[list[PisteDemandee], str, Context], Awaitable[SansQuestion | Elicit[BaseModel]]]:
    """Le résolveur qui départage les titres ambigus d'une demande, en cherchant par `deezer`."""

    async def departager(pistes: list[PisteDemandee], nom: str, ctx: Context) -> SansQuestion | Elicit[BaseModel]:
        ambigus: list[tuple[int, Ambigu]] = []
        for rang, demandee in enumerate(pistes):
            if demandee.deezer is None:
                cherche = TitreCherche(artiste=demandee.artiste, titre=demandee.titre)
                try:
                    resultat = resultat_de(cherche, await deezer.chercher(cherche))
                except DeezerIndisponible as erreur:
                    raise ToolError(TEXTES.deezer_indisponible) from erreur
                if isinstance(resultat, Ambigu):
                    ambigus.append((rang, resultat))
        if not ambigus or len(ambigus) > LISTES.ambigus_au_plus or not _sait_demander(ctx):
            return SansQuestion()
        return Elicit(TEXTES.listes.departage.format(nom=nom), _formulaire(ambigus))

    return departager
