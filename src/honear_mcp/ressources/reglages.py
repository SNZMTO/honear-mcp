"""Les réglages du serveur : chaque durée, chaque borne et chaque quota, nommés une fois, lus partout ailleurs.

Les durées sont en secondes.
"""

from dataclasses import dataclass

from honear_mcp.ressources.honear import PARTIE_DE_HONEAR

UN_JOUR = 24 * 3600
TEXTES_JUGES_EN_MEMOIRE = 4096  # Le jugement normalise chaque texte une fois : une saisie piégée coûte quatre fois moins.


@dataclass(frozen=True)
class ReglagesDeDeezer:
    """Deezer, que le MCP partage avec Honear : même machine, même adresse IP, même limite.

    Son API admet 50 appels par 5 secondes. Le MCP en prend 10, et Honear passe de 40 à 30 avant que le MCP soit en ligne : la
    somme laisse alors 10 de marge. Quand Deezer dit qu'on va trop vite (son code 4), on attend une fenêtre et on réessaie,
    quelques fois. Au-delà de tant d'appels qui attendent leur tour, on n'en prend plus : mieux vaut dire « réessaie » que faire
    attendre tout le monde.
    """

    fenetre: float
    """La fenêtre sur laquelle Deezer compte les appels."""
    par_fenetre: int
    """Les appels que le MCP s'autorise par fenêtre."""
    essais: int
    """Combien de fois on demande au plus, quand Deezer dit qu'on va trop vite."""
    attente: float
    """Le temps qu'on laisse à Deezer pour répondre."""
    file_au_plus: int
    """Combien d'appels peuvent attendre leur tour à la fois."""
    recherche_gardee: float
    """Combien de temps une recherche se garde, et les pistes qu'elle a vues : redemander le même titre, ou faire une liste des
    pistes trouvées, ne coûte rien pendant ce temps."""
    gardees_au_plus: int
    """Combien de recherches on garde au plus."""
    vues_au_plus: int
    """Combien de pistes vues dans les recherches on garde au plus."""
    resultats: int
    """Combien de pistes une recherche demande : l'original est presque toujours dans les premières."""


DEEZER = ReglagesDeDeezer(
    fenetre=5,
    par_fenetre=10,
    essais=3,
    attente=8,
    file_au_plus=40,
    recherche_gardee=3600,
    gardees_au_plus=2000,
    vues_au_plus=20000,
    resultats=10,
)


@dataclass(frozen=True)
class ReglagesDesTitres:
    """Ce qu'on cherche chez Deezer en un appel d'outil, et ce qu'on en rend."""

    au_plus: int
    """Combien de titres on cherche à la fois : de quoi une playlist entière en deux appels."""
    longueur_au_plus: int
    """La longueur d'un nom d'artiste ou de titre, en signes."""
    candidats_au_plus: int
    """Combien de candidats on propose pour un titre ambigu."""
    ressemblance_au_moins: float
    """Entre 0 et 1 : en dessous, une piste ne ressemble pas assez à ce qu'on cherche pour être proposée."""


TITRES = ReglagesDesTitres(au_plus=25, longueur_au_plus=200, candidats_au_plus=4, ressemblance_au_moins=0.6)


@dataclass(frozen=True)
class ReglagesDuServeur:
    """Le serveur HTTP : où il écoute, quels noms il sert, combien de sessions il tient.

    Les clients d'avant la version 2026-07-28 du protocole ouvrent une session : elles sont bornées, et oubliées après un temps
    sans nouvelles.
    """

    hote: str
    """Où il écoute, si la variable d'environnement HONEAR_MCP_HOTE n'en dit pas un autre (dans le conteneur : 0.0.0.0)."""
    port: int
    hotes: tuple[str, ...]
    """Les noms sous lesquels on répond (l'en-tête Host) ; tout autre reçoit une erreur 421."""
    origines: tuple[str, ...]
    """Les pages d'où un navigateur peut appeler (l'en-tête Origin)."""
    sessions_au_plus: int
    session_oubliee: float
    port_interne: int
    """Le port où Honear lit les listes (`/listes/<id>`) : le frontal ne le relaie pas, il ne sort pas de la machine."""
    requetes_par_adresse: int
    """Combien de requêtes au MCP une adresse IP envoie au plus par fenêtre. Large : claude.ai ou ChatGPT appellent depuis
    quelques adresses pour tous leurs utilisateurs ; cette borne-là n'arrête qu'un script. Les vraies bornes sont celles de
    Deezer et des listes, qui valent pour tout le monde."""
    fenetre_par_adresse: float
    adresses_au_plus: int
    """Combien d'adresses on suit à la fois, en mémoire ; une adresse s'oublie quand sa fenêtre est passée."""
    journal_lu_au_plus: int
    """Le journal lit au plus ce début du corps d'une requête, pour y trouver la méthode MCP, l'outil et ce que dit le client."""
    journal_entete_au_plus: int
    """Un en-tête recopié au journal est coupé à cette longueur."""


SERVEUR = ReglagesDuServeur(
    hote="127.0.0.1",
    port=8790,
    port_interne=8791,
    requetes_par_adresse=120,
    fenetre_par_adresse=60,
    adresses_au_plus=10000,
    hotes=("127.0.0.1:*", "localhost:*", "mcp.honear.fr"),
    origines=("http://127.0.0.1:*", "http://localhost:*"),
    sessions_au_plus=200,
    session_oubliee=1800,
    journal_lu_au_plus=16384,
    journal_entete_au_plus=160,
)


@dataclass(frozen=True)
class ReglagesDesListes:
    """Les listes sur mesure : leurs bornes, leur durée de vie, et où elles sont rangées.

    Une liste vit 30 jours après sa création, puis 30 jours après chaque partie où Honear l'a lue. Les bornes sont en signes ;
    un nom de liste, un surnom ou une anecdote trop longs sont refusés, pas coupés.
    """

    pistes_au_moins: int
    """Ce que Honear demande pour une partie (`PARTIE_DE_HONEAR`, qu'il exporte) : une liste plus courte ne se jouerait pas."""
    pistes_au_plus: int
    nom_au_plus: int
    surnoms_au_plus: int
    """Par piste, et pour l'artiste comme pour le titre."""
    surnom_au_plus: int
    anecdote_au_plus: int
    listes_au_plus: int
    """Combien de listes vivent à la fois, toutes personnes confondues ; au-delà, une nouvelle prend la place de la plus vieille
    que personne n'a jouée."""
    vie: float
    connu_au_moins: int
    """Le rang Deezer d'un titre que presque tout le monde reconnaît : « que des titres connus » garde ceux-là."""
    artiste_au_plus: int
    """Combien de pistes d'un même artiste une liste garde, si on ne dit rien."""
    ambigus_au_plus: int
    """Combien de titres ambigus on fait départager d'un coup ; au-delà, on rend les candidats au modèle."""
    proposees: int
    """Combien de titres les prompts demandent au modèle de proposer, si on ne dit rien : de quoi une face de Honear."""
    octets: int
    """L'aléa d'un identifiant de liste : 12 octets, 96 bits, 16 signes ; personne ne devine celui d'un autre."""
    dossier: str
    """Où les listes sont rangées, un fichier chacune, si la variable d'environnement HONEAR_MCP_LISTES n'en dit pas un autre."""


LISTES = ReglagesDesListes(
    pistes_au_moins=PARTIE_DE_HONEAR.pistes_au_moins,
    pistes_au_plus=50,
    nom_au_plus=60,
    surnoms_au_plus=3,
    surnom_au_plus=40,
    anecdote_au_plus=160,
    listes_au_plus=2000,
    vie=30 * UN_JOUR,
    connu_au_moins=500000,
    artiste_au_plus=2,
    ambigus_au_plus=5,
    proposees=20,
    octets=12,
    dossier="/var/lib/honear-mcp/listes",
)


@dataclass(frozen=True)
class ReglagesDeHonear:
    """Ce que le MCP sait de Honear : où l'on joue une liste."""

    lien_de_liste: str
    """Le lien qui ouvre une room sur une liste ; `{id}` est son identifiant."""


HONEAR = ReglagesDeHonear(lien_de_liste="https://honear.fr/?liste={id}")


@dataclass(frozen=True)
class ReglagesDeLAccueil:
    """La page d'accueil de mcp.honear.fr : où elle est rangée, et ce qu'un navigateur peut y charger (rien que sa feuille de
    style, reconnue à son empreinte)."""

    page: str
    """Son fichier, à côté de ce module."""
    csp: str
    """La politique de sécurité du contenu ; `{style}` est l'empreinte de la feuille de style de la page."""


ACCUEIL = ReglagesDeLAccueil(
    page="accueil.html",
    csp="default-src 'none'; style-src '{style}'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
)
