"""L'heure et l'attente : le seul endroit qui les lit. Le reste reçoit une horloge ; les tests en donnent une fausse."""

import time
from datetime import UTC, datetime
from typing import Protocol

import anyio


class Horloge(Protocol):
    """Ce qu'une horloge sait faire : dire l'heure qu'il est, et attendre."""

    def maintenant(self) -> float:
        """Des secondes qui ne reculent jamais, depuis un instant quelconque : de quoi mesurer un écart, pas dire la date."""
        ...

    def monde(self) -> float:
        """L'heure du monde, en secondes depuis 1970 : de quoi dater ce qui survit à un redémarrage."""
        ...

    async def attendre(self, secondes: float) -> None:
        """Rend la main après tant de secondes."""
        ...


class HorlogeDuSysteme:
    """L'horloge de la machine."""

    def maintenant(self) -> float:
        """L'horloge monotone du système."""
        return time.monotonic()

    def monde(self) -> float:
        """L'heure du système."""
        return time.time()

    async def attendre(self, secondes: float) -> None:
        """Dort tant de secondes, sans bloquer les autres tâches."""
        await anyio.sleep(secondes)


def jour(instant: float) -> str:
    """Le jour d'un instant du monde, en temps universel, comme on l'écrit pour une machine : « 2026-11-15 »."""
    return datetime.fromtimestamp(instant, UTC).date().isoformat()
