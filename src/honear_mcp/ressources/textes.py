"""Les textes que lisent les gens et leur modèle : ce que dit le serveur, le nom et le mode d'emploi des outils, leurs refus.

Un texte qui attend une valeur la nomme entre accolades, et le code la remplit avec `str.format`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TexteDOutil:
    """Le nom qu'un client montre pour un outil ou une ressource, et le mode d'emploi que lit le modèle."""

    titre: str
    description: str


@dataclass(frozen=True)
class TexteDePrompt:
    """Un prompt prêt : son nom, ce qu'il fait, et le message qu'il envoie au modèle."""

    titre: str
    description: str
    message: str


@dataclass(frozen=True)
class TextesDesListes:
    """Ce que dit `creer_liste` quand il demande, et quand il refuse."""

    departage: str
    """La question posée à l'hôte quand des titres sont ambigus."""
    candidat: str
    aucun: str
    ambigus: str
    """Le refus, quand on ne peut pas demander : les candidats, pour que le modèle demande lui-même."""
    ligne_ambigue: str
    candidat_ambigu: str
    trop_peu: str
    ligne_ecartee: str
    inconnue: str


@dataclass(frozen=True)
class Textes:
    """Tous les textes du serveur."""

    instructions: str
    """Ce que le modèle lit du serveur en s'y branchant."""
    chercher_titres: TexteDOutil
    creer_liste: TexteDOutil
    une_liste: TexteDOutil
    listes: TextesDesListes
    deezer_indisponible: str
    soiree: TexteDePrompt
    theme: TexteDePrompt
    importer: TexteDePrompt


_COMMENT = (
    "Vérifie-les avec chercher_titres et remplace ceux qui ont un drapeau. Ajoute des surnoms seulement quand un titre ou un "
    "artiste se dit autrement, une anecdote seulement quand tu en es sûr, puis enregistre la liste avec creer_liste, donne "
    "le lien, et dis comment la jouer."
)

TEXTES = Textes(
    instructions=(
        "Honear (https://honear.fr) est un blind test entre potes : les téléphones jouent, un écran montre la partie. Ce serveur "
        "vérifie chez Deezer les titres que tu proposes pour une playlist sur mesure, puis l’enregistre pour que Honear la "
        "joue : c’est toi qui choisis les titres, les surnoms et les anecdotes ; lui dit ce qui existe, ce qui a un extrait de "
        "30 secondes, ce qui cloche, et rend le lien de la partie."
    ),
    chercher_titres=TexteDOutil(
        titre="Chercher des titres chez Deezer",
        description=(
            "Retrouve chez Deezer des titres (un artiste et un titre chacun), jusqu’à {au_plus} à la fois, rendus dans l’ordre "
            "donné. Chacun est « trouve » (la piste, son rang de popularité chez Deezer, sa durée en secondes et ses drapeaux), "
            "« ambigu » (des candidats proches, à départager par leur identifiant deezer) ou « introuvable ». Les drapeaux "
            "disent ce qui se joue mal au blind test : sans_extrait, live, remix, karaoke, reprise, doublon (déjà plus haut "
            "dans la demande). Devant un drapeau, propose une autre version ou un autre titre."
        ),
    ),
    creer_liste=TexteDOutil(
        titre="Enregistrer une liste pour Honear",
        description=(
            "Enregistre une playlist sur mesure, de {au_moins} à {au_plus} pistes, et rend le lien qui la joue sur honear.fr. "
            "Donne pour chaque piste l’identifiant deezer que chercher_titres a rendu (sinon, elle est cherchée, et un titre "
            "ambigu est demandé à la personne quand son client le permet). Les surnoms sont d’autres façons justes de dire "
            "l’artiste ou le titre, qui ne lui ressemblent pas (« Matthieu Chedid » pour « -M- ») : n’en donne pas pour ce que "
            "Honear accepte déjà, les accents, les majuscules, des fautes de frappe, ce qui s’entend pareil, "
            "les articles, ce qui est entre parenthèses, l’invité d’un feat., ni un mot du nom tapé parmi d’autres (« Maître "
            "Gims » vaut déjà « GIMS », « Puff Daddy » vaut déjà « Diddy »). L’anecdote est une phrase courte et vérifiable, "
            "montrée à la révélation ; rien d’inventé. « croissante » range du plus connu au moins connu et Honear joue la "
            "liste dans cet ordre ; « telle_quelle » la laisse mélanger. Une liste est oubliée {jours} jours après sa dernière "
            "partie, ou plus tôt si le serveur est plein et que personne ne l’a jouée. Pour la jouer : ouvrir le lien sur un "
            "écran que tout le monde voit, toucher « On pose un disque ? » et faire sa pochette ; la liste attend dans le bac, "
            "il reste à toucher « Celle-là », et chacun rejoint la room avec son téléphone."
        ),
    ),
    une_liste=TexteDOutil(
        titre="Une liste enregistrée",
        description="Une liste que creer_liste a enregistrée, par son identifiant : ses pistes, leurs surnoms, leurs anecdotes.",
    ),
    listes=TextesDesListes(
        departage="Plusieurs pistes ressemblent à ces titres. Lesquelles mettre dans « {nom} » ?",
        candidat="{titre} — {artiste} ({album})",
        aucun="Aucune de celles-là : ne pas la mettre",
        ambigus=(
            "Rien n’est enregistré : ces titres sont ambigus. Demande à la personne lesquels garder, puis rappelle creer_liste "
            "avec leur identifiant deezer.\n{lignes}"
        ),
        ligne_ambigue="- {artiste} — {titre} : {candidats}",
        candidat_ambigu="{deezer} ({titre}, {artiste}, {album})",
        trop_peu=(
            "Rien n’est enregistré : il reste {gardees} pistes jouables, il en faut au moins {au_moins}. Remplace celles-ci, "
            "ou ajoutes-en :\n{lignes}"
        ),
        ligne_ecartee="- {artiste} — {titre} : {raison}",
        inconnue="Aucune liste vivante sous cet identifiant : elle a pu être oubliée, faute d’avoir été jouée.",
    ),
    deezer_indisponible=(
        "Deezer ne répond pas en ce moment, ou trop de recherches attendent leur tour : réessaie dans une minute. Ce qui a déjà "
        "été retrouvé ne sera pas recherché une seconde fois."
    ),
    soiree=TexteDePrompt(
        titre="Une playlist pour une soirée",
        description="Une playlist Honear pour une occasion (un anniversaire, une crémaillère), d’après les goûts des invités.",
        message=(
            "Prépare une playlist pour un blind test Honear : {occasion}. Les invités, et ce qu’ils aiment : {invites}. Choisis "
            "{nombre} titres que la plupart reconnaîtront dès les premières secondes, variés, qui collent à l’occasion. "
            + _COMMENT
        ),
    ),
    theme=TexteDePrompt(
        titre="Une playlist sur un thème",
        description="Une playlist Honear sur un thème qui n’existe nulle part : « une couleur dans le titre », « nés en 2003 ».",
        message=(
            "Prépare une playlist pour un blind test Honear sur ce thème : {theme}. Choisis {nombre} titres qui y répondent "
            "vraiment, du plus connu au plus pointu. " + _COMMENT
        ),
    ),
    importer=TexteDePrompt(
        titre="Importer une playlist d’ailleurs",
        description="Une playlist Honear tirée d’une capture d’écran, d’une liste collée ou d’une affiche de festival.",
        message=(
            "Voici une playlist d’ailleurs : {source}. Relève chaque artiste et chaque titre tels qu’ils y sont, sans en "
            "inventer ni en oublier, et garde son ordre (telle_quelle). " + _COMMENT
        ),
    ),
)
