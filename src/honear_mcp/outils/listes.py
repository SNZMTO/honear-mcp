"""L'outil `creer_liste` et la ressource `honear://listes/{id}` : enregistrer une playlist sur mesure, que Honear sait jouer.

Le modèle donne les pistes (de préférence par l'identifiant que `chercher_titres` a rendu), leurs surnoms et leurs anecdotes ;
l'outil les retrouve chez Deezer, écarte ce qui jouerait mal, range, enregistre, et rend le lien de la partie. Rien n'est
enregistré tant qu'un titre reste ambigu, ou qu'il reste trop peu de pistes.
"""

from typing import Annotated, Literal

from mcp.server.mcpserver import AcceptedElicitation, Context, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from honear_mcp.outils.departage import AUCUN, choix_de, refus_des_ambigus, resolveur
from honear_mcp.regles.liste import Ecartee, NomDeListe, PisteDeLaListe, PisteDemandee, Raison, ranger, surnoms_utiles
from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.deezer import Deezer, DeezerIndisponible
from honear_mcp.reseau.horloge import jour
from honear_mcp.reseau.rangement import Rangement
from honear_mcp.ressources.reglages import HONEAR, LISTES, UN_JOUR
from honear_mcp.ressources.textes import TEXTES
from honear_mcp.sources.correspondance import Ambigu, Introuvable, Piste, piste_de, resultat_de


class ListeCreee(BaseModel):
    """La liste enregistrée, et de quoi la jouer."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    id: str
    nom: str
    lien: str
    """Le lien qui ouvre une room sur cette liste, sur honear.fr."""
    oubliee_le: str
    """Le jour où elle sera oubliée si personne ne la joue ; chaque partie lui redonne toute une vie."""
    pistes: list[PisteDeLaListe]
    """Dans l'ordre où Honear les jouera, quand la difficulté monte."""
    ecartees: list[Ecartee]


async def _retrouver(deezer: Deezer, demandee: PisteDemandee, choix: str) -> Piste | Raison | Ambigu:
    """La piste de Deezer d'une demande, la raison de l'écarter, ou le titre ambigu que personne n'a départagé."""
    if demandee.deezer is not None:
        trouvee = await deezer.piste(demandee.deezer)
        return piste_de(trouvee) if trouvee is not None else "introuvable"
    cherche = TitreCherche(artiste=demandee.artiste, titre=demandee.titre)
    resultat = resultat_de(cherche, await deezer.chercher(cherche))
    if isinstance(resultat, Introuvable):
        return "introuvable"
    if not isinstance(resultat, Ambigu):
        return resultat.piste
    if choix == AUCUN:
        return "ecartee_par_l_hote"
    return next((c for c in resultat.candidats if str(c.deezer) == choix), resultat)


def _refus_trop_peu(gardees: int, ecartees: list[Ecartee]) -> ToolError:
    lignes = [TEXTES.listes.ligne_ecartee.format(artiste=e.artiste, titre=e.titre, raison=e.raison) for e in ecartees]
    texte = TEXTES.listes.trop_peu.format(gardees=gardees, au_moins=LISTES.pistes_au_moins, lignes="\n".join(lignes))
    return ToolError(texte)


def ajouter_les_listes(serveur: MCPServer, deezer: Deezer, rangement: Rangement) -> None:
    """Ajoute l'outil et la ressource au serveur : on cherche par `deezer`, on range dans `rangement`."""

    @serveur.tool(
        name="creer_liste",
        title=TEXTES.creer_liste.titre,
        description=TEXTES.creer_liste.description.format(
            au_moins=LISTES.pistes_au_moins, au_plus=LISTES.pistes_au_plus, jours=round(LISTES.vie / UN_JOUR)
        ),
        annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True),
    )
    async def creer_liste(
        nom: NomDeListe,
        pistes: Annotated[list[PisteDemandee], Field(min_length=LISTES.pistes_au_moins, max_length=LISTES.pistes_au_plus)],
        departage: Annotated[ElicitationResult[BaseModel], Resolve(resolveur(deezer))],
        ctx: Context,
        *,
        ordre: Literal["croissante", "telle_quelle"] = "croissante",
        seulement_connus: bool = False,
        artiste_au_plus: Annotated[int, Field(ge=1, le=LISTES.pistes_au_plus)] = LISTES.artiste_au_plus,
    ) -> ListeCreee:
        reponse = departage.data if isinstance(departage, AcceptedElicitation) else None
        retenues: list[PisteDeLaListe] = []
        ecartees: list[Ecartee] = []
        ambigus: list[Ambigu] = []
        for rang, demandee in enumerate(pistes):
            try:
                retrouvee = await _retrouver(deezer, demandee, choix_de(reponse, rang) if reponse is not None else "")
            except DeezerIndisponible as erreur:
                raise ToolError(TEXTES.deezer_indisponible) from erreur
            await ctx.report_progress(rang + 1, len(pistes))
            if isinstance(retrouvee, Ambigu):
                ambigus.append(retrouvee)
            elif isinstance(retrouvee, str):
                ecartees.append(Ecartee(artiste=demandee.artiste, titre=demandee.titre, raison=retrouvee))
            elif "sans_extrait" in retrouvee.drapeaux:
                ecartees.append(Ecartee(artiste=retrouvee.artiste, titre=retrouvee.titre, raison="sans_extrait"))
            else:
                surnoms = surnoms_utiles(demandee.surnoms, retrouvee.artiste, retrouvee.titre)
                retenues.append(
                    PisteDeLaListe(
                        deezer=retrouvee.deezer,
                        titre=retrouvee.titre,
                        artiste=retrouvee.artiste,
                        rang=retrouvee.rang,
                        surnoms=surnoms,
                        anecdote=demandee.anecdote,
                    )
                )
        if ambigus:
            raise refus_des_ambigus(ambigus)
        croissante = ordre == "croissante"
        gardees, refusees = ranger(
            retenues, croissante=croissante, seulement_connus=seulement_connus, artiste_au_plus=artiste_au_plus
        )
        ecartees += [Ecartee(artiste=p.artiste, titre=p.titre, raison=raison) for p, raison in refusees]
        if len(gardees) < LISTES.pistes_au_moins:
            raise _refus_trop_peu(len(gardees), ecartees)
        liste = rangement.creer(nom, gardees, dans_l_ordre=croissante)
        return ListeCreee(
            id=liste.id,
            nom=liste.nom,
            lien=HONEAR.lien_de_liste.format(id=liste.id),
            oubliee_le=jour(liste.jusqua),
            pistes=liste.pistes,
            ecartees=ecartees,
        )

    @serveur.resource(
        "honear://listes/{id_de_liste}",
        title=TEXTES.une_liste.titre,
        description=TEXTES.une_liste.description,
        mime_type="application/json",
    )
    def une_liste(id_de_liste: str) -> str:
        liste = rangement.lire(id_de_liste)
        if liste is None:
            raise ResourceNotFoundError(TEXTES.listes.inconnue)
        return liste.model_dump_json()
