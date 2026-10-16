"""Une horloge qu'on avance à la main : attendre y est instantané, et le temps qui passe se lit après coup."""

import anyio.lowlevel

DEBUT_DU_MONDE = 1792108800.0


class FausseHorloge:
    """L'horloge des tests : elle part de zéro, et n'avance que quand quelqu'un attend, ou qu'un test l'avance."""

    def __init__(self) -> None:
        self.heure = 0.0
        self.attentes: list[float] = []

    def maintenant(self) -> float:
        return self.heure

    def monde(self) -> float:
        """Le 16 octobre 2026 à minuit, temps universel, plus ce qui a passé."""
        return DEBUT_DU_MONDE + self.heure

    async def attendre(self, secondes: float) -> None:
        self.attentes.append(secondes)
        self.heure += secondes
        await anyio.lowlevel.checkpoint()
