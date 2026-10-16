"""Ce que Deezer est, et qu'on ne choisit pas : l'adresse de son API publique et les codes de ses refus."""

from dataclasses import dataclass


@dataclass(frozen=True)
class APIDeDeezer:
    """L'API publique de Deezer, sans compte ni clé."""

    adresse: str
    quota: int
    """Le code de « Quota limit exceeded » : on va trop vite."""
    introuvable: frozenset[int]
    """Les codes de « no data » (rien à cette adresse) et d'un paramètre qui ne va pas."""


API_DE_DEEZER = APIDeDeezer(adresse="https://api.deezer.com", quota=4, introuvable=frozenset({800, 801, 802}))
