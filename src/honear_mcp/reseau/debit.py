"""Les limites de débit : celle des appels du MCP à Deezer, et celle des requêtes de chaque adresse au MCP.

La première est celle de Honear (`sonTour`, dans `src/reseau/musique.ts`) : une fenêtre glissante, où l'on oublie les appels
sortis de la fenêtre ; s'il n'y a plus de place, on attend que le plus ancien en sorte. La seconde refuse au lieu d'attendre.
"""

from collections import deque

from honear_mcp.reseau.horloge import Horloge


class Fenetre:
    """Les appels des dernières secondes, pour n'en laisser passer que tant."""

    def __init__(self, par_fenetre: int, duree: float, horloge: Horloge) -> None:
        """Une fenêtre vide, qui laisse passer `par_fenetre` appels toutes les `duree` secondes."""
        self._par_fenetre = par_fenetre
        self._duree = duree
        self._horloge = horloge
        self._appels: deque[float] = deque()

    async def son_tour(self) -> None:
        """Attend que la fenêtre laisse passer un appel, et le compte."""
        while True:
            maintenant = self._horloge.maintenant()
            while self._appels and self._appels[0] <= maintenant - self._duree:
                self._appels.popleft()
            if len(self._appels) < self._par_fenetre:
                break
            await self._horloge.attendre(self._appels[0] + self._duree - maintenant)
        self._appels.append(self._horloge.maintenant())


class ParAdresse:
    """Tant de requêtes au plus par adresse, sur une fenêtre fixe qui part de sa première requête ; puis l'adresse est oubliée.

    On ne garde que l'adresse, son compte et l'heure de sa première requête, en mémoire, et tant d'adresses au plus : les plus
    anciennes s'oublient d'abord. Une fois par fenêtre au plus, la première requête venue fait oublier toutes les adresses dont
    la fenêtre est passée : une adresse ne reste pas plus d'une fenêtre après la sienne, tant que des requêtes arrivent.
    """

    def __init__(self, par_fenetre: int, duree: float, au_plus: int, horloge: Horloge) -> None:
        """Personne n'est encore compté."""
        self._par_fenetre = par_fenetre
        self._duree = duree
        self._au_plus = au_plus
        self._horloge = horloge
        self._comptes: dict[str, tuple[float, int]] = {}
        self._menage = horloge.maintenant()
        """Quand on a oublié les adresses passées pour la dernière fois."""

    def attente(self, adresse: str) -> float:
        """Compte une requête de cette adresse : 0 si elle passe, sinon combien de secondes attendre avant la prochaine."""
        self.menage()
        maintenant = self._horloge.maintenant()
        debut, compte = self._comptes.get(adresse, (maintenant, 0))
        if debut + self._duree <= maintenant:
            debut, compte = maintenant, 0
        if compte >= self._par_fenetre:
            return debut + self._duree - maintenant
        self._comptes.pop(adresse, None)
        self._comptes[adresse] = (debut, compte + 1)
        if len(self._comptes) > self._au_plus:
            self._oublier(maintenant)
        return 0

    def menage(self) -> None:
        """Oublie les adresses dont la fenêtre est passée, une fois par fenêtre au plus : à appeler aussi pour une requête qui ne
        compte pas ici, pour que les adresses s'oublient même quand plus rien ne compte."""
        maintenant = self._horloge.maintenant()
        if self._menage + self._duree <= maintenant:
            self._oublier(maintenant)

    def _oublier(self, maintenant: float) -> None:
        self._menage = maintenant
        for passee in [a for a, (debut, _) in self._comptes.items() if debut + self._duree <= maintenant]:
            del self._comptes[passee]
        while len(self._comptes) > self._au_plus:
            del self._comptes[next(iter(self._comptes))]
