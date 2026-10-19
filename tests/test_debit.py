"""La limite de chaque adresse, sur une horloge qu'on avance à la main : ce qu'elle garde en mémoire, et quand elle l'oublie."""

from honear_mcp.reseau.debit import ParAdresse
from honear_mcp.ressources.reglages import SERVEUR
from tests.fausse_horloge import FausseHorloge


def test_une_adresse_s_oublie_une_fois_sa_fenetre_passee_meme_si_peu_d_adresses_viennent() -> None:
    horloge = FausseHorloge()
    limite = ParAdresse(SERVEUR.requetes_par_adresse, SERVEUR.fenetre_par_adresse, SERVEUR.adresses_au_plus, horloge)
    assert limite.attente("192.0.2.1") == 0
    horloge.heure += SERVEUR.fenetre_par_adresse - 1
    assert limite.attente("192.0.2.2") == 0
    assert set(limite._comptes) == {"192.0.2.1", "192.0.2.2"}
    # Sa fenêtre passée, la première requête venue, d'où qu'elle vienne, la fait oublier : on ne garde que ce qui compte encore.
    horloge.heure += 1
    assert limite.attente("192.0.2.3") == 0
    assert set(limite._comptes) == {"192.0.2.2", "192.0.2.3"}
    horloge.heure += SERVEUR.fenetre_par_adresse
    assert limite.attente("192.0.2.3") == 0
    assert set(limite._comptes) == {"192.0.2.3"}


def test_les_sessions_d_une_adresse_s_oublient_meme_si_plus_personne_n_en_ouvre() -> None:
    # Le serveur ne compte que les requêtes qui ouvrent une session ; toutes les autres font le ménage (`serveurs/public.py`).
    horloge = FausseHorloge()
    sessions = ParAdresse(SERVEUR.sessions_par_adresse, SERVEUR.fenetre_des_sessions, SERVEUR.adresses_au_plus, horloge)
    assert sessions.attente("192.0.2.1") == 0
    horloge.heure += SERVEUR.fenetre_des_sessions - 1
    sessions.menage()
    assert set(sessions._comptes) == {"192.0.2.1"}
    horloge.heure += 1
    sessions.menage()
    assert not sessions._comptes
