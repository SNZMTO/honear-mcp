"""Les textes du mini blind test : ce que lit le modèle de ses outils, et ce qu'il dit quand il ne peut pas jouer.

Ceux de la fenêtre elle-même (les boutons, les verdicts) sont dans `interface/src/textes.ts` : c'est elle qui les montre.
Un texte qui attend une valeur la nomme entre accolades, et le code la remplit avec `str.format`.
"""

from dataclasses import dataclass

from honear_mcp.ressources.textes import TexteDOutil


@dataclass(frozen=True)
class TextesDuMini:
    """Tous les textes du mini blind test, côté serveur."""

    fenetre: str
    jouer_ici: TexteDOutil
    piste: TexteDOutil
    repondre: TexteDOutil
    reveler: TexteDOutil
    nom: str
    prete: str
    sans_fenetre_liste: str
    sans_fenetre_titres: str
    une_seule_source: str
    trop_peu: str
    pleines: str
    inconnue: str
    reservee: str
    sans_extrait: str


TEXTES_DU_MINI = TextesDuMini(
    fenetre="Le mini blind test de Honear",
    jouer_ici=TexteDOutil(
        titre="Jouer au blind test ici",
        description=(
            "Ouvre un mini blind test dans la conversation, de {au_moins} à {au_plus} pistes ({defaut} si on ne dit rien) : "
            "l’extrait de 30 secondes, un champ pour répondre, la révélation. Donne soit une liste que creer_liste a "
            "enregistrée (son identifiant), soit des titres pour un thème (chacun est cherché chez Deezer). La réponse "
            "n’arrive jamais jusqu’à toi avant la révélation : la fenêtre la garde pour la personne qui joue. Si la fenêtre "
            "ne s’affiche pas, le message dit comment jouer sur honear.fr."
        ),
    ),
    piste=TexteDOutil(titre="La piste à écouter", description="L’extrait de la piste en cours d’une partie, sans sa réponse."),
    repondre=TexteDOutil(titre="Répondre", description="Juge une saisie sur la piste en cours, comme Honear la juge."),
    reveler=TexteDOutil(titre="Révéler", description="Révèle la piste en cours, et passe à la suivante."),
    nom="Le mini blind test",
    prete=(
        "Le mini blind test « {nom} » est prêt : {total} pistes, à jouer dans la fenêtre. Ne donne aucun indice sur les titres "
        "à venir : la fenêtre dira le score à la fin."
    ),
    sans_fenetre_liste=(
        "Si aucune fenêtre ne s’affiche, ce client ne sait pas la montrer : la liste se joue aussi sur honear.fr, {lien}"
    ),
    sans_fenetre_titres=(
        "Si aucune fenêtre ne s’affiche, ce client ne sait pas la montrer : enregistre ces titres avec creer_liste, et la "
        "liste se jouera sur honear.fr."
    ),
    une_seule_source="Donne soit l’identifiant d’une liste, soit des titres, l’un ou l’autre.",
    trop_peu="Il n’y a que {n} pistes jouables, il en faut au moins {au_moins} : propose d’autres titres.",
    pleines="Trop de parties sont en cours en ce moment : réessaie dans quelques minutes.",
    inconnue="Cette partie n’existe pas, ou plus (une heure sans jouer) : relance jouer_ici.",
    reservee="Cet outil est celui de la fenêtre du mini blind test, pas du modèle.",
    sans_extrait="Deezer n’a plus d’extrait pour cette piste : révèle-la pour passer à la suivante.",
)
