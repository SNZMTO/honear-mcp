"""Les parties du mini blind test, en mémoire : chacune sous un identifiant que le serveur tire, oubliée une heure après son
dernier geste ; tant au plus à la fois. Plein, le serveur oublie la plus vieille partie que personne n'a jouée, comme pour
les listes : un script qui en ouvre en boucle ne chasse que des parties jamais jouées. Le protocole n'a plus de session : c'est
cet identifiant, passé à chaque outil de la fenêtre, qui tient la partie d'un appel à l'autre.
"""

from honear_mcp.regles.mini import PartieDuMini
from honear_mcp.reseau.hasard import identifiant
from honear_mcp.reseau.horloge import Horloge
from honear_mcp.ressources.reglages_du_mini import MINI


class Parties:
    """Les parties en cours."""

    def __init__(self, horloge: Horloge) -> None:
        """Aucune partie ; l'heure se lit sur `horloge`."""
        self._horloge = horloge
        self._parties: dict[str, tuple[float, PartieDuMini, bool]] = {}
        """Chaque partie : jusqu'à quand elle vit, où elle en est, et si quelqu'un y a déjà fait un geste."""

    @property
    def en_cours(self) -> int:
        """Combien de parties vivent encore."""
        self._oublier()
        return len(self._parties)

    def ouvrir(self, partie: PartieDuMini) -> str | None:
        """Range une partie neuve et rend son identifiant. Plein, la plus vieille partie jamais jouée lui laisse sa place ; rien
        si toutes ont été jouées."""
        self._oublier()
        if len(self._parties) >= MINI.parties_au_plus:
            jamais_jouees = [i for i, (_, _, jouee) in self._parties.items() if not jouee]
            if not jamais_jouees:
                return None
            del self._parties[min(jamais_jouees, key=lambda i: self._parties[i][0])]
        id_de_partie = identifiant()
        self._parties[id_de_partie] = (self._horloge.maintenant() + MINI.vie, partie, False)
        return id_de_partie

    def lire(self, id_de_partie: str) -> PartieDuMini | None:
        """La partie de cet identifiant, si elle vit encore."""
        self._oublier()
        gardee = self._parties.get(id_de_partie)
        return gardee[1] if gardee is not None else None

    def garder(self, id_de_partie: str, partie: PartieDuMini) -> None:
        """La partie après un geste : elle vit de nouveau une heure, et compte comme jouée."""
        self._parties[id_de_partie] = (self._horloge.maintenant() + MINI.vie, partie, True)

    def _oublier(self) -> None:
        maintenant = self._horloge.maintenant()
        for passee in [i for i, (jusqua, _, _) in self._parties.items() if jusqua <= maintenant]:
            del self._parties[passee]
