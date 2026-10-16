"""Ce que les tests de `creer_liste` demandent : des pistes par leur nom, ou par leur identifiant chez Deezer, et les deux façons
d'appeler l'outil, qu'il enregistre ou qu'il refuse."""

from mcp import Client
from mcp.types import TextContent

from honear_mcp.outils.listes import ListeCreee

type Demande = dict[str, object]

DAFT_PUNK: Demande = {"artiste": "Daft Punk", "titre": "One More Time"}
STROMAE: Demande = {"artiste": "Stromae", "titre": "Alors on danse"}
GIMS: Demande = {"artiste": "Gims", "titre": "Bella"}
QUEEN_MAL_ECRIT: Demande = {"artiste": "Queen", "titre": "Bohemian Rapsody"}
INCONNU: Demande = {"artiste": "Zqxwv Plughxyz", "titre": "Vwqzk Trlmpf"}


def par_id(deezer: int, artiste: str, titre: str, **reste: object) -> Demande:
    return {"artiste": artiste, "titre": titre, "deezer": deezer, **reste}


AUTOUR_DE_BELLA = [
    par_id(571858272, "Naestro", "Bella Ciao"),
    par_id(126024227, "Niska", "Elle avait son Djo"),
    par_id(2992386141, "Accaoui", "Ma Bella"),
    par_id(3154947201, "Gina Bella", "Broken-Hearted"),
    par_id(68893313, "Mulatu Astatke", "Gambella"),
]
"""Des pistes que la recherche de « Bella » (GIMS) fait voir, chacune d'un autre artiste : de quoi faire une liste assez longue
pour une partie de Honear (10 pistes au moins)."""
PEU_CONNUES = [
    *AUTOUR_DE_BELLA[2:],
    par_id(807920502, "Ritchie", "Gisella"),
    par_id(2896214501, "Gisella", "Bibi Anrafa (Mbiwi)"),
]
"""Celles d'entre elles que peu de gens reconnaîtraient (un rang Deezer sous 500 000)."""


async def creer(client: Client, pistes: list[Demande], **reglages: object) -> ListeCreee:
    resultat = await client.call_tool("creer_liste", {"nom": "Les 30 ans de Léa", "pistes": pistes, **reglages})
    assert not resultat.is_error, resultat.content
    return ListeCreee.model_validate(resultat.structured_content)


async def refus(client: Client, pistes: list[Demande], **reglages: object) -> str:
    resultat = await client.call_tool("creer_liste", {"nom": "Les 30 ans de Léa", "pistes": pistes, **reglages})
    (texte,) = resultat.content
    assert resultat.is_error
    assert isinstance(texte, TextContent)
    return texte.text
