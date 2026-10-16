"""`chercher_titres`, appelé comme un vrai client l'appelle, contre les réponses enregistrées chez Deezer."""

import pytest
from mcp import Client
from mcp.types import TextContent

from honear_mcp.outils.titres import Recherche
from honear_mcp.ressources.reglages import DEEZER, TITRES
from honear_mcp.ressources.textes import TEXTES
from honear_mcp.sources.correspondance import Ambigu, Introuvable, Trouve
from tests.fausse_horloge import FausseHorloge
from tests.faux_deezer import FauxDeezer

pytestmark = pytest.mark.anyio

DAFT_PUNK = {"artiste": "Daft Punk", "titre": "One More Time"}
STROMAE = {"artiste": "Stromae", "titre": "Alors on danse"}
QUEEN_MAL_ECRIT = {"artiste": "Queen", "titre": "Bohemian Rapsody"}
GIMS = {"artiste": "Gims", "titre": "Bella"}
INCONNU = {"artiste": "Zqxwv Plughxyz", "titre": "Vwqzk Trlmpf"}


async def chercher(client: Client, *titres: dict[str, str]) -> Recherche:
    resultat = await client.call_tool("chercher_titres", {"titres": list(titres)})
    assert not resultat.is_error, resultat.content
    return Recherche.model_validate(resultat.structured_content)


async def test_l_outil_se_presente_en_lecture_seule_avec_ses_bornes(client: Client) -> None:
    (outil,) = [o for o in (await client.list_tools()).tools if o.name == "chercher_titres"]
    assert outil.title == TEXTES.chercher_titres.titre
    assert outil.annotations is not None
    assert outil.annotations.read_only_hint
    assert outil.input_schema["properties"]["titres"]["maxItems"] == TITRES.au_plus


async def test_un_lot_rend_chaque_titre_dans_l_ordre_avec_ce_qui_cloche(client: Client, faux_deezer: FauxDeezer) -> None:
    recherche = await chercher(client, DAFT_PUNK, STROMAE, QUEEN_MAL_ECRIT, GIMS, INCONNU, DAFT_PUNK)
    daft_punk, stromae, queen, gims, inconnu, encore = recherche.resultats

    # L'original, pas le « 12 Mix » ni le live d'Alive 2007, ni les reprises d'autres artistes.
    assert isinstance(daft_punk, Trouve)
    assert (daft_punk.piste.deezer, daft_punk.piste.album, daft_punk.piste.drapeaux) == (3135553, "Discovery", [])
    # La version de l'album, que Deezer appelle « Radio Edit » : Honear la montre et l'attend sans cela.
    assert isinstance(stromae, Trouve)
    assert (stromae.piste.deezer, stromae.piste.titre, stromae.piste.titre_complet) == (
        6297555,
        "Alors on danse",
        "Alors on danse (Radio Edit)",
    )
    # Une faute dans le titre : des candidats, l'original d'abord, le live ensuite et dit tel.
    assert isinstance(queen, Ambigu)
    assert [(c.deezer, c.drapeaux) for c in queen.candidats[:2]] == [(4091936671, []), (4091936771, ["live"])]
    assert len(queen.candidats) <= TITRES.candidats_au_plus
    # « Gims » est le « GIMS » de Deezer.
    assert isinstance(gims, Trouve)
    assert gims.piste.deezer == 72717420
    assert isinstance(inconnu, Introuvable)
    # Le même titre demandé deux fois : la seconde est un doublon, et Deezer n'est pas rappelé.
    assert isinstance(encore, Trouve)
    assert encore.piste.drapeaux == ["doublon"]
    assert len(faux_deezer.appels) == 5


async def test_le_modele_lit_le_resultat_en_texte(client: Client) -> None:
    resultat = await client.call_tool("chercher_titres", {"titres": [GIMS]})
    (texte,) = resultat.content
    assert isinstance(texte, TextContent)
    assert Recherche.model_validate_json(texte.text) == Recherche.model_validate(resultat.structured_content)


async def test_chaque_titre_cherche_fait_avancer_la_progression(client: Client) -> None:
    vues: list[tuple[float, float | None]] = []

    # Les noms sont ceux qu'attend le SDK (ProgressFnT).
    async def progression(progress: float, total: float | None, message: str | None) -> None:
        vues.append((progress, total))

    await client.call_tool("chercher_titres", {"titres": [DAFT_PUNK, GIMS]}, progress_callback=progression)
    assert vues == [(1, 2), (2, 2)]


async def test_trop_de_titres_ou_un_nom_vide_sont_refuses_avant_deezer(client: Client, faux_deezer: FauxDeezer) -> None:
    trop = await client.call_tool("chercher_titres", {"titres": [GIMS] * (TITRES.au_plus + 1)})
    vide = await client.call_tool("chercher_titres", {"titres": [{"artiste": "  ", "titre": "Bella"}]})
    long = await client.call_tool("chercher_titres", {"titres": [{"artiste": "x" * (TITRES.longueur_au_plus + 1), "titre": "y"}]})
    assert trop.is_error
    assert vide.is_error
    assert long.is_error
    assert faux_deezer.appels == []


async def test_deezer_qui_dit_qu_on_va_trop_vite_est_redemande_une_fenetre_plus_tard(
    client: Client, faux_deezer: FauxDeezer, horloge: FausseHorloge
) -> None:
    faux_deezer.refus_a_venir = DEEZER.essais - 1
    recherche = await chercher(client, GIMS)
    assert isinstance(recherche.resultats[0], Trouve)
    assert len(faux_deezer.appels) == DEEZER.essais
    assert horloge.attentes == [DEEZER.fenetre] * (DEEZER.essais - 1)


async def test_deezer_qui_refuse_toujours_ou_ne_repond_pas_donne_une_phrase_a_lire(
    client: Client, faux_deezer: FauxDeezer
) -> None:
    faux_deezer.refus_a_venir = DEEZER.essais
    refuse = await client.call_tool("chercher_titres", {"titres": [GIMS]})
    faux_deezer.refus_a_venir = 0
    faux_deezer.muet = True
    muet = await client.call_tool("chercher_titres", {"titres": [DAFT_PUNK]})
    # Le SDK fait précéder la phrase du nom de l'outil (« Error executing tool chercher_titres: »).
    for resultat in (refuse, muet):
        (texte,) = resultat.content
        assert resultat.is_error
        assert isinstance(texte, TextContent)
        assert texte.text.endswith(f": {TEXTES.deezer_indisponible}")


async def test_une_recherche_gardee_se_redemande_une_fois_son_temps_passe(
    client: Client, faux_deezer: FauxDeezer, horloge: FausseHorloge
) -> None:
    await chercher(client, GIMS)
    horloge.heure += DEEZER.recherche_gardee - 1
    await chercher(client, GIMS)
    assert len(faux_deezer.appels) == 1
    horloge.heure += 1
    await chercher(client, GIMS)
    assert len(faux_deezer.appels) == 2
