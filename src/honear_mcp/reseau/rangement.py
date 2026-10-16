"""Le rangement des listes : un fichier JSON par liste, dans un seul dossier, jamais à moitié écrit.

Une liste s'écrit dans un fichier à côté, vidé sur le disque, puis mis à sa place d'un coup (`Path.replace`) : un arrêt en plein
milieu laisse l'ancienne version ou la nouvelle, jamais un mélange. Une liste dont le temps est passé est oubliée quand on la
lit, et toutes celles-là quand on en crée une : le rangement sait, sans les relire, jusqu'à quand chacune vit ; il ne relit
tout le dossier que si son compte ne tombe plus juste. Quand le rangement est plein, une nouvelle liste prend la place de la
plus vieille que personne n'a jouée : un script qui en crée en boucle n'efface que des listes jamais jouées, et n'empêche
personne d'en créer. Un identifiant n'est jamais qu'un nom de fichier : rien qui remonte d'un dossier.
"""

import os
import re
from pathlib import Path

from pydantic import ValidationError

from honear_mcp.regles.liste import Liste, PisteDeLaListe
from honear_mcp.reseau.hasard import identifiant
from honear_mcp.reseau.horloge import Horloge
from honear_mcp.ressources.reglages import LISTES

_IDENTIFIANT = re.compile(r"[A-Za-z0-9_-]+")


def _a_oublier_d_abord(liste: Liste) -> tuple[bool, float]:
    """L'ordre où l'on fait de la place : celles que personne n'a jouées, puis celles qui s'oublieraient les premières."""
    return liste.jouee, liste.jusqua


class Rangement:
    """Les listes d'un dossier."""

    def __init__(self, dossier: Path, horloge: Horloge) -> None:
        """Le rangement de `dossier`, qu'on crée s'il n'existe pas ; les dates se lisent sur `horloge`."""
        self._dossier = dossier
        self._horloge = horloge
        self._connues: dict[str, tuple[bool, float]] | None = None
        """Ce qu'on sait de chaque liste rangée, sans la relire : jouée ou pas, et jusqu'à quand elle vit."""
        dossier.mkdir(parents=True, exist_ok=True)

    def nombre(self) -> int:
        """Combien de listes sont rangées, oubliées ou pas encore."""
        return sum(1 for _ in self._dossier.glob("*.json"))

    def creer(self, nom: str, pistes: list[PisteDeLaListe], *, dans_l_ordre: bool) -> Liste:
        """Range une nouvelle liste sous un identifiant neuf, pour toute sa vie ; plein, le rangement oublie de quoi lui faire
        de la place."""
        connues = self._ce_qu_on_sait()
        maintenant = self._horloge.monde()
        for passee in [i for i, (_, jusqua) in connues.items() if jusqua <= maintenant]:
            self._oublier(passee)
        de_trop = len(connues) + 1 - LISTES.listes_au_plus
        for oubliee in sorted(connues, key=connues.__getitem__)[: max(de_trop, 0)]:
            self._oublier(oubliee)
        liste = Liste(id=identifiant(), nom=nom, dans_l_ordre=dans_l_ordre, pistes=pistes, jusqua=self._fin_de_vie())
        self._ecrire(liste)
        return liste

    def lire(self, id_de_liste: str) -> Liste | None:
        """La liste de cet identifiant, si elle existe et vit encore."""
        fichier = self._fichier(id_de_liste)
        if fichier is None or not fichier.is_file():
            return None
        try:
            liste = Liste.model_validate_json(fichier.read_bytes())
        except ValidationError:
            return None
        if liste.jusqua <= self._horloge.monde():
            self._oublier(liste.id)
            return None
        return liste

    def jouee(self, id_de_liste: str) -> Liste | None:
        """La liste qu'une partie va jouer : elle vit de nouveau toute une vie à partir de maintenant."""
        liste = self.lire(id_de_liste)
        if liste is None:
            return None
        prolongee = liste.model_copy(update={"jusqua": self._fin_de_vie(), "jouee": True})
        self._ecrire(prolongee)
        return prolongee

    def oublier_les_vieilles(self) -> list[Liste]:
        """Oublie les listes dont le temps est passé, et ce qu'une écriture interrompue a pu laisser ; rend celles qui vivent."""
        for fichier in self._dossier.glob(".*.tmp"):
            fichier.unlink(missing_ok=True)
        vivantes = [liste for fichier in self._dossier.glob("*.json") if (liste := self.lire(fichier.stem)) is not None]
        self._connues = {liste.id: _a_oublier_d_abord(liste) for liste in vivantes}
        return vivantes

    def _ce_qu_on_sait(self) -> dict[str, tuple[bool, float]]:
        """Ce qu'on sait de chaque liste : lu sur le disque la première fois, tenu à jour ensuite, et relu si le dossier compte
        d'autres fichiers que ceux qu'on connaît (posés par une autre main, ou laissés par un arrêt)."""
        if self._connues is None or len(self._connues) != self.nombre():
            self.oublier_les_vieilles()
        return self._connues if self._connues is not None else {}

    def _oublier(self, id_de_liste: str) -> None:
        (self._dossier / f"{id_de_liste}.json").unlink(missing_ok=True)
        if self._connues is not None:
            self._connues.pop(id_de_liste, None)

    def _fin_de_vie(self) -> float:
        return self._horloge.monde() + LISTES.vie

    def _fichier(self, id_de_liste: str) -> Path | None:
        return self._dossier / f"{id_de_liste}.json" if _IDENTIFIANT.fullmatch(id_de_liste) else None

    def _ecrire(self, liste: Liste) -> None:
        provisoire = self._dossier / f".{liste.id}.tmp"
        with provisoire.open("wb") as fichier:
            fichier.write(liste.model_dump_json().encode())
            fichier.flush()
            os.fsync(fichier.fileno())
        provisoire.replace(self._dossier / f"{liste.id}.json")
        if self._connues is not None:
            self._connues[liste.id] = _a_oublier_d_abord(liste)
        dossier = os.open(self._dossier, os.O_RDONLY)
        try:
            os.fsync(dossier)
        finally:
            os.close(dossier)
