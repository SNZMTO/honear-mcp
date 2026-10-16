"""Le réseau vers Deezer : la limite de débit du MCP, et la file d'attente qui ne s'allonge pas sans fin."""

import anyio
import pytest

from honear_mcp.regles.titres import TitreCherche
from honear_mcp.reseau.debit import Fenetre
from honear_mcp.reseau.deezer import Deezer, DeezerIndisponible
from honear_mcp.ressources.reglages import DEEZER
from tests.fausse_horloge import FausseHorloge
from tests.faux_deezer import FauxDeezer

pytestmark = pytest.mark.anyio

GIMS = TitreCherche(artiste="Gims", titre="Bella")


async def test_jamais_plus_d_appels_par_fenetre_que_le_mcp_ne_s_en_autorise(horloge: FausseHorloge) -> None:
    fenetre = Fenetre(DEEZER.par_fenetre, DEEZER.fenetre, horloge)
    heures: list[float] = []
    for _ in range(DEEZER.par_fenetre * 3 + 1):
        await fenetre.son_tour()
        heures.append(horloge.heure)
    for heure in heures:
        assert sum(heure <= h < heure + DEEZER.fenetre for h in heures) <= DEEZER.par_fenetre
    # Le premier lot part tout de suite, chacun des suivants une fenêtre plus tard.
    assert heures[DEEZER.par_fenetre - 1] == 0
    assert heures[-1] == DEEZER.fenetre * 3


async def test_au_dela_de_la_file_on_ne_fait_plus_attendre_personne(deezer: Deezer, faux_deezer: FauxDeezer) -> None:
    faux_deezer.retenu = anyio.Event()
    reponses: list[int] = []

    async def chercher() -> None:
        reponses.append(len(await deezer.chercher(GIMS)))

    async with anyio.create_task_group() as taches:
        for _ in range(DEEZER.file_au_plus):
            taches.start_soon(chercher)
        await anyio.wait_all_tasks_blocked()
        assert deezer.en_attente == DEEZER.file_au_plus
        with pytest.raises(DeezerIndisponible):
            await deezer.chercher(GIMS)
        faux_deezer.retenu.set()
    assert len(reponses) == DEEZER.file_au_plus
    assert deezer.en_attente == 0
    assert deezer.gardees == 1
