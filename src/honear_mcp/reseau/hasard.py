"""Le hasard : le seul endroit qui en tire, par `secrets`, que personne ne prédit ; les identifiants, et l'ordre d'une partie."""

import secrets

from honear_mcp.ressources.reglages import LISTES


def identifiant() -> str:
    """Un identifiant (d'une liste, d'une partie) : 96 bits d'aléa, en 16 signes qui passent dans une adresse."""
    return secrets.token_urlsafe(LISTES.octets)


def melanger(n: int) -> list[int]:
    """Les rangs de 0 à n - 1 dans un ordre que personne ne prédit (Fisher-Yates, tiré par `secrets`)."""
    ordre = list(range(n))
    for i in range(n - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    return ordre
