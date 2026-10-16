"""Les prompts prêts, tels qu'un client les liste et les remplit."""

import pytest
from mcp import Client
from mcp.types import TextContent

from honear_mcp.ressources.reglages import LISTES

pytestmark = pytest.mark.anyio


async def test_trois_prompts_disent_au_modele_quoi_choisir_et_quoi_en_faire(client: Client) -> None:
    assert sorted(p.name for p in (await client.list_prompts()).prompts) == ["importer", "soiree", "theme"]
    soiree = await client.get_prompt("soiree", {"occasion": "les 30 ans de Léa", "invites": "Léa, fan de Beyoncé"})
    (message,) = soiree.messages
    assert isinstance(message.content, TextContent)
    assert "les 30 ans de Léa" in message.content.text
    assert f"{LISTES.proposees} titres" in message.content.text
    assert "creer_liste" in message.content.text
