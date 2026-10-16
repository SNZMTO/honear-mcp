# Les données personnelles

Le MCP de Honear se sert sans compte. Il ne demande ni nom, ni e-mail, ni rien des comptes de Honear, qu'il ne lit jamais.

## Ce qu'il reçoit, ce qu'il garde

| Quoi | D'où | Gardé où, combien de temps |
|---|---|---|
| Des noms d'artistes et de titres | le modèle du client, par `chercher_titres` | en mémoire, une heure (le cache des recherches), puis oublié ; jamais écrit sur disque |
| La recherche envoyée à Deezer | le serveur, vers l'API publique de Deezer | chez Deezer, selon ses règles ; elle part de l'adresse du serveur, pas de celle du client |
| L'adresse IP d'un client | la connexion, par le frontal | en mémoire, une minute, pour compter ses requêtes (120 au plus) ; jamais écrite : le journal du MCP ne la lit pas |
| Ce que fait un client : la méthode demandée, l'outil appelé, le code de la réponse, son logiciel et ce qu'il dit savoir faire | chaque requête au MCP | le journal du conteneur, que journald fait tourner ; ni adresse ni contenu |
| Une session d'ancien client | le protocole 2025-11-25 | en mémoire, 30 minutes sans nouvelles au plus ; un identifiant tiré au hasard, rien d'autre |
| Une liste : son nom, ses pistes, leurs surnoms et leurs anecdotes | le modèle du client, par `creer_liste` | un fichier sur le serveur, 30 jours après sa création ou sa dernière partie, puis effacé (plus tôt si le serveur en garde déjà 2 000 et que personne ne l'a jouée) ; rien ne la relie à qui l'a créée |
| Les choix de l'hôte entre des titres ambigus | la personne, par le formulaire de son client | le temps de l'appel ; seul le titre choisi entre dans la liste |
| Une partie du mini blind test, et ce qu'on y tape | la fenêtre, dans la conversation | en mémoire, une heure après son dernier geste, puis oubliée |

Le thème d'une playlist (« les 30 ans de Léa ») reste dans la conversation, chez le client : le serveur ne reçoit que des
artistes et des titres.

Le nom d'une liste et ses anecdotes sont écrits par le modèle, à la demande de la personne : ils peuvent porter un prénom (« Les
30 ans de Léa »). Ils ne servent qu'à jouer la liste : quiconque a son lien la voit, comme une playlist partagée, et
personne d'autre. L'identifiant ne se devine pas (96 bits d'aléa), aucune page ne liste les listes, et elles ne vont pas dans
les statistiques de Honear. Le texte est nettoyé avant d'être gardé (`regles/nettoyage.py`).

L'assistant d'exploitation, pour l'éditeur seul, lit les statistiques de Honear : des compteurs, et les recherches du bac telles
que Honear les garde déjà (son propre registre). Il n'en garde rien : il les rend à qui les demande, dans sa conversation.

Une partie du mini blind test vit en mémoire, une heure après son dernier geste : ses pistes, ce qu'on a trouvé, les points ;
rien de qui joue. Ce qu'on tape s'y juge et s'oublie. Les extraits et les pochettes, la fenêtre les lit directement chez
Deezer (sur dzcdn.net), qui reçoit donc l'adresse IP de qui joue, comme pour n'importe quelle page web ; et ses polices, chez le
MCP, qui ne garde pas cette adresse.
