# Le MCP de Honear : les playlists sur mesure

Un serveur MCP pour Honear (https://honear.fr). Ce que l'IA sait faire et le jeu non : une playlist qui n'existe nulle part
(« des chansons avec une couleur dans le titre », « les 30 ans de Léa, fan de Beyoncé et de variété »). Le modèle du client
choisit les titres ; le serveur fait le travail fiable. Il n'appelle jamais de modèle lui-même, ni aucun service payant.

Ce que le serveur sait faire aujourd'hui :

- **`chercher_titres`** retrouve chez Deezer jusqu'à 25 titres à la fois, et dit de chacun s'il est trouvé (la piste, son rang
  de popularité, sa durée), ambigu (des candidats, à départager) ou introuvable, avec ce qui le jouerait mal : pas d'extrait,
  live, remix, karaoké, reprise, doublon.
- **`creer_liste`** enregistre une playlist de 10 à 50 pistes, avec leurs surnoms acceptés et leurs anecdotes, et rend le lien
  qui la joue sur honear.fr. Il écarte ce qui jouerait mal (pas d'extrait, doublon, titre peu connu, artiste trop présent),
  range du plus connu au moins connu, et fait départager par l'hôte un titre ambigu quand son client sait montrer un
  formulaire (l'élicitation) ; sinon il rend les candidats au modèle.
- **`jouer_ici`** ouvre un mini blind test dans la conversation (MCP Apps), sur une liste ou sur des titres pour un thème :
  l'extrait de 30 secondes, un champ pour répondre, la révélation, à l'allure de Honear (sa palette, ses polices). Le modèle
  n'en voit ni les titres ni les réponses ; la fenêtre les obtient par trois outils qui ne sont qu'à elle (`mini_piste`,
  `mini_repondre`, `mini_reveler`), et dit le score au modèle à la fin. Un client sans fenêtre reçoit le lien pour jouer sur
  honear.fr.
- **`honear://listes/{id}`**, une ressource : la liste telle que Honear la lira.
- **Trois prompts** : `soiree` (une occasion, des invités), `theme`, `importer` (une capture, une liste collée, une affiche).
- **`/`** : une page pour qui ouvre l'adresse dans un navigateur (ce que c'est, comment l'ajouter, ce qu'il garde), sans script.
- **`/sante`** dit s'il attend Deezer, combien de recherches il garde, et combien de listes il range.
- **`/listes/{id}`**, sur un second port que le frontal ne relaie pas : ce que Honear lit pour jouer une liste.

Et pour Mateo seul, sur le VPS, un second serveur, en stdio : **l'assistant d'exploitation** (`honear-exploitation`). Il lit
l'état de Honear et du MCP, les statistiques de Honear (à sa clé), l'échéance des certificats de honear.fr, mateosan.fr et
mcp.honear.fr, la CI du dernier commit, et répond à « je peux déployer là ? ». Il ne met rien en ligne, ne redémarre rien,
n'écrit rien ; le serveur public ne lit aucun de ses modules.

La suite est dans « Ce qui attend » : la mise en ligne, l'anecdote et le lien direct dans Honear, le mini blind test dans la
conversation, la vitrine.

## Lancer

```
uv sync --frozen
HONEAR_MCP_LISTES=/tmp/listes uv run honear-mcp
```

Le serveur écoute sur http://127.0.0.1:8790/mcp, et Honear lit les listes sur http://127.0.0.1:8791/listes/{id}. Les listes
se rangent dans le dossier que nomme `HONEAR_MCP_LISTES` (sinon `/var/lib/honear-mcp/listes`, celui du conteneur). Pour
l'essayer :

- depuis Claude Code : `claude mcp add --transport http honear-local http://127.0.0.1:8790/mcp` ;
- avec MCP Inspector, sans modèle :
  `npx -y @modelcontextprotocol/inspector@2.11.0 --cli http://127.0.0.1:8790/mcp --transport http --method tools/list`.

Il appelle alors le vrai Deezer, depuis l'adresse IP de la machine : sur le VPS, c'est celle de Honear (voir le budget, dans
`NOTES-TECHNIQUES.md`).

## Les couches

Chaque couche ne lit que celles du dessous, et `tests/test_sources.py` le vérifie.

| Couche | Ce qu'elle fait | Ce qu'elle lit hors du paquet |
|---|---|---|
| `ressources` | les réglages et les textes : des données, jamais du code | rien |
| `regles` | ce qui se décide sur un texte ou une liste, sans réseau ni horloge | Pydantic |
| `sources` | ce que Deezer répond, lu sans l'appeler ; les adresses à lui demander | Pydantic |
| `reseau` | ce qui appelle Deezer, range les listes sur le disque, lit l'heure, tire un identifiant | httpx2, anyio |
| `outils` | les outils MCP, minces | le SDK MCP |
| `serveurs` | l'assemblage, et ce qui le sert en HTTP | le SDK MCP, Starlette, uvicorn |

## Les modules, un rôle chacun

- `ressources/reglages.py` : chaque durée, borne et quota (le budget Deezer, les bornes des titres et des listes, le serveur
  HTTP, le lien d'une liste sur honear.fr).
- `ressources/deezer.py` : ce que Deezer est et qu'on ne choisit pas : l'adresse de son API, les codes de ses refus.
- `ressources/textes.py` : tout ce que lisent les gens et leur modèle (les instructions du serveur, les outils, les refus).
- `ressources/accueil.html` : la page d'accueil, servie telle quelle.
- `ressources/reglages_du_mini.py`, `ressources/textes_du_mini.py` : ceux du mini blind test ; `ressources/mini-blind-test.html`,
  le gabarit de sa fenêtre, et `ressources/mini-blind-test.js`, son script, construit par `interface/` (jamais retouché ici).
- `ressources/polices/` : les polices de Honear et leur licence, que Honear y écrit.
- `ressources/reglages_d_exploitation.py`, `ressources/textes_d_exploitation.py` : ceux de l'assistant d'exploitation, à part :
  le serveur public ne les lit pas.
- `regles/titres.py` : un titre cherché ; comparer deux noms, ôter l'habillage d'un titre, lire sa version (les drapeaux).
  Les règles de comparaison et d'habillage sont celles de Honear.
- `regles/nettoyage.py` : le texte qui finira sur un écran, nettoyé (forme Unicode, signes invisibles qui agissent, liens).
- `regles/liste.py` : une liste et ses pistes, leurs bornes, les surnoms utiles, et le rangement par difficulté.
- `regles/jugement.py`, `regles/parties.py` : le jugement d'une saisie et la saisie libre de Honear, portés en Python.
- `regles/mini.py` : une partie du mini blind test, ce qu'on a trouvé de la piste en cours, et les points.
- `ressources/honear.py` : ce que le MCP reprend de Honear (les réglages du jugement, sa part de Deezer), écrit par Honear.
- `sources/deezer.py` : les pistes et les refus d'une réponse de Deezer ; l'adresse d'une recherche, celle d'une fiche.
- `sources/correspondance.py` : trouvé, ambigu ou introuvable, et les doublons d'un lot.
- `reseau/horloge.py` : la seule horloge, celle qui mesure et celle qui date.
- `reseau/hasard.py` : le seul tirage, celui des identifiants de liste.
- `reseau/rangement.py` : les listes sur le disque, écrites d'un coup, oubliées quand leur temps est passé.
- `reseau/parties.py` : les parties du mini blind test, en mémoire, sous un identifiant que le serveur tire.
- `reseau/debit.py` : les limites de débit : celle des appels à Deezer (une fenêtre glissante, celle de Honear), celle des
  requêtes de chaque adresse au MCP.
- `reseau/deezer.py` : les appels à Deezer, sous la limite, avec leurs essais, leur file bornée, leur cache, et les pistes
  vues dans les recherches.
- `outils/titres.py` : l'outil `chercher_titres`.
- `outils/listes.py` : l'outil `creer_liste` et la ressource d'une liste.
- `outils/departage.py` : le formulaire qui fait départager les titres ambigus, et le refus qui rend leurs candidats.
- `outils/prompts.py` : les trois prompts.
- `outils/mini.py`, `outils/mini_blind_test.py` : les outils du mini blind test (MCP Apps), et ce qu'ils font.
- `sources/exploitation.py`, `reseau/exploitation.py`, `outils/exploitation.py`, `serveurs/exploitation.py` : l'assistant
  d'exploitation, de la lecture des réponses de Honear et de GitHub à son serveur en stdio.
- `serveurs/public.py` : le serveur public, ses deux applications web (`/mcp`, `/` et `/sante` ; `/listes/{id}` pour Honear),
  la limite par adresse, et son point d'entrée.
- `serveurs/accueil.py` : la route de la page d'accueil, sous sa politique de sécurité du contenu.
- `serveurs/fenetre.py` : la page de la fenêtre du mini blind test, assemblée au démarrage, et la route de ses polices.
- `serveurs/journal.py` : une ligne au journal par requête au MCP (la méthode, l'outil, le client et ses capacités), sans
  adresse ni contenu.
- `interface/` : le script de la fenêtre, en TypeScript strict, sans framework (`@modelcontextprotocol/ext-apps`, esbuild).
- `Dockerfile`, `deploiement/` : l'image, le conteneur, la mise en ligne (`HEBERGEMENT.md`).
- `publication/publier.sh` : publie un commit de ce dépôt dans le dépôt public, d'un bloc, après avoir vérifié qu'aucun secret
  ni l'adresse du VPS ne part ; `publication/kit-mateosan.md`, de quoi présenter le projet sur mateosan.fr.
- `README.md` et `.github/captures/` : la vitrine du dépôt public.
- `tests/faux_deezer.py` et `tests/deezer/` : le faux Deezer et ses réponses enregistrées ; `tests/fausse_horloge.py`.
- `tests/jugement-de-honear.json` : la table des saisies que Honear a jugées, contre laquelle le portage est jugé.

## Ce qui a été tranché le 16 octobre 2026

Les six décisions de la phase 0, que Mateo a validées :

- **Le SDK officiel** (`mcp` 2.3.0), son extension MCP Apps pour le mini blind test, et `@modelcontextprotocol/ext-apps`
  dans la page de l'interface.
- **Les listes appartiennent au MCP** : un fichier JSON par liste, réécrit de façon atomique, sous un identifiant non devinable
  (`secrets`, 96 bits), bornées, oubliées 30 jours après leur dernière partie. Honear les lit sur un réseau Docker interne,
  `honear-listes` ; le public passe par le réseau `honear-mcp`, celui du frontal.
- **Le quota de Deezer** : 10 appels par 5 secondes pour le MCP, Honear passe de 40 à 30 ; chacun réessaie quand Deezer dit
  qu'on va trop vite, et tout ce qui peut l'être est gardé.
- **Le jugement** du mini blind test est un portage Python de celui de Honear, vérifié contre une table de cas que Honear
  génère depuis ses propres tests.
- **L'assistant d'exploitation** passe par stdio, sur le VPS ou par SSH, jamais par mcp.honear.fr ; la clé des statistiques
  lui est copiée par Mateo, et ne part que dans un en-tête.
- **Les outils** se nomment en français ; une partie du mini blind test vit en mémoire sous un identifiant que le serveur donne.

Et en construisant le socle :

- **`chercher_titres` arrive dès le socle** : sans lui, le faux Deezer et le réseau n'auraient servi à rien.
- **La recherche se fait en vrac** (`Daft Punk One More Time`) : la recherche avancée de Deezer (`artist:"…" track:"…"`) ne
  trouve plus rien. C'est la comparaison des noms, celle de Honear, qui trie ; un appel par titre.
- **Un titre trouvé** a le nom et l'artiste cherchés, à l'habillage près ; parmi ses versions, celle sans drapeau, la plus
  populaire. Sinon, les pistes qui lui ressemblent assez (0,6 sur 1) sont des candidats, la plus proche d'abord.
- **Les drapeaux** se lisent dans le titre et sa version ; le karaoké et la reprise aussi dans le nom de l'artiste. L'album
  n'en dit rien : « Best of REMIXED » marquerait tout un disque.
- **Un refus de Deezer** fait échouer l'appel entier, avec une phrase à lire : ce qui a déjà été retrouvé est gardé une
  heure, et un nouvel appel ne le redemande pas.
- **Le journal des requêtes est le nôtre** (`serveurs/journal.py`) : celui d'uvicorn garderait l'adresse IP de chaque client.
  Le nôtre dit ce que demande un client et ce qu'on lui répond, sans adresse ni contenu ; ajouté quand claude.ai a refusé de
  se brancher sans dire pourquoi.
- **Les anciens clients** (protocole 2025-11-25) ont des sessions : 200 au plus, oubliées après 30 minutes sans nouvelles.

Et en écrivant les listes :

- **`creer_liste` enregistre tout ou rien** : un titre encore ambigu, ou moins de 10 pistes jouables, et rien n'est rangé ; le
  refus dit pourquoi, titre par titre. Une liste à moitié juste serait à refaire de toute façon.
- **Les pistes vues dans une recherche** se gardent une heure, par leur identifiant : une liste faite des pistes que
  `chercher_titres` vient de trouver ne rappelle pas Deezer. Une autre se lit sur sa fiche (`/track/{id}`).
- **Le titre et l'artiste gardés sont ceux de Deezer**, pas ceux du modèle : c'est ce que Honear relira.
- **Les surnoms** : on oublie ceux que la saisie libre de Honear trouve déjà avec le vrai nom ou un surnom gardé avant eux. Elle
  en accepte beaucoup : les articles, les fautes, ce qui se dit pareil, et un mot du nom tapé parmi d'autres, si bien que
  « Maître Gims » vaut déjà « GIMS » et « Puff Daddy » déjà « Diddy » ; il reste « Matthieu Chedid » pour « -M- ». Le mode
  d'emploi de l'outil le dit aussi au modèle.
- **La difficulté** : « croissante » range par le rang Deezer, du plus écouté au moins écouté, avant de compter les artistes
  (d'un artiste trop présent, on garde ses titres les plus connus) ; Honear la jouera dans cet ordre. « Que des titres
  connus » garde un rang de 500 000 au moins.
- **Le départage** passe par un résolveur du SDK, qui pose sa question avant l'outil : sur le protocole 2026-07-28 dans la
  réponse même, sur l'ancien par une requête. Le formulaire a un choix par titre ambigu (ses candidats, et « aucune »), 5 au
  plus ; un client qui ne sait pas montrer de formulaire, ou un hôte qui refuse, reçoit les candidats à faire choisir.
- **Lire une liste, pour Honear, c'est la jouer** : elle revit 30 jours. La ressource MCP la montre sans la prolonger.
- **Le texte nettoyé** : forme NFC, ni caractère de contrôle ni signe de format invisible (dont ceux qui retournent le sens de
  l'écriture), ni lien. Les bornes se comptent avant le nettoyage, et un texte trop long est refusé, pas coupé.
- **Ni le nom d'une liste ni ce que les gens cherchent ne vont au journal** : celui des appels à Deezer est coupé.

Et en portant le jugement de Honear :

- **Une seule vérité, écrite par Honear** : `npm run exporter-pour-le-mcp -- ~/honear-mcp`, dans Honear, écrit les réglages
  du jugement et la part de Deezer du jeu (`ressources/honear.py`), et une table de saisies jugées par le jeu
  (`tests/jugement-de-honear.json`) : les cas de ses tests (`tests/cas-du-jugement.ts`, qu'ils partagent), et des variantes
  tirées d'une graine (une lettre en moins, deux inversées, un accent, un son voisin, une autre réponse). Ici, on ne les
  retouche jamais : un portage qui dérive, ou un jeu qui change de jugement, rougit `tests/test_jugement.py`.
- **Les expressions du jeu, telles quelles** : en JavaScript, `\b` est en ASCII et `\s` connaît tous les blancs d'Unicode ;
  le portage dit l'un et l'autre explicitement.
- **La somme des deux budgets Deezer** se vérifie : celui du MCP plus celui que Honear exporte laisse 10 appels de marge.

Et en construisant le mini blind test :

- **La réponse ne passe jamais par le modèle** : `jouer_ici` ne rend qu'un identifiant de partie, un nom et un nombre de
  pistes. Les outils qui rendent un extrait, un verdict ou une réponse sont réservés à la fenêtre (`visibility: ["app"]` :
  l'hôte ne les montre pas au modèle) et refusent, de plus, un client qui n'a pas dit savoir afficher une fenêtre MCP Apps.
  Ce qu'une fenêtre reçoit de ses propres appels ne va pas au modèle ; elle ne lui dit le score et les pistes qu'à la fin.
- **Le jugement est celui de Honear**, porté et vérifié contre sa table : un point par partie trouvée (l'artiste, le titre),
  avec les surnoms d'une liste. Les titres d'une partie de thème sont cherchés chez Deezer ; ceux qu'il n'a pas, ou sans
  extrait, sont passés.
- **Une partie vit en mémoire**, sous un identifiant tiré par `secrets`, une heure après son dernier geste, 200 au plus :
  le protocole n'a plus de session, c'est cet identifiant, passé à chaque outil, qui la tient. Une liste se joue dans son ordre
  si sa difficulté monte ; sinon, et pour un thème, dans un ordre tiré au hasard.
- **L'extrait se relit avant d'être servi** : celui qu'on a vu sert s'il n'expire pas dans les deux minutes, sinon sa fiche
  (`/track/{id}`) est relue chez Deezer, sans le cache.
- **La fenêtre a l'allure de Honear** : sa palette et ses polices viennent de Honear (`npm run exporter-pour-le-mcp`), les
  polices se servent sur `/polices/<fichier>` à toute page (la fenêtre vit sur le domaine de l'hôte). Sa politique de contenu
  ne laisse charger que mcp.honear.fr (les polices) et `*.dzcdn.net` (les extraits, les pochettes).
- **Le script de la fenêtre est construit, et versionné** : `interface/` (TypeScript strict, esbuild, le paquet
  `@modelcontextprotocol/ext-apps` avec ses dépendances embarquées) l'écrit dans `ressources/mini-blind-test.js`, et la CI le
  reconstruit pour vérifier qu'il n'a pas bougé. L'image du serveur reste sans Node.
- **Essayé dans un vrai navigateur**, avec un hôte d'essai (l'`AppBridge` du même paquet) qui joue une partie de bout en bout :
  l'accueil, l'écoute, un verdict, la révélation et sa pochette, la fin, et le bilan reçu par le modèle. Reste l'essai dans
  claude.ai, le vrai hôte.

Et en préparant la mise en ligne :

- **La limite par adresse est large** : 120 requêtes par minute. claude.ai et ChatGPT appellent depuis quelques adresses pour
  tous leurs utilisateurs : une borne serrée les couperait tous ensemble. Elle n'arrête qu'un script ; les vraies bornes valent
  pour tout le monde (le budget Deezer et sa file, le nombre de listes). L'adresse est celle que donne le frontal
  (`X-Forwarded-For`), le seul à joindre ce port ; elle ne sert qu'à compter, en mémoire, une minute.
- **L'image** : Python 3.13 et uv figés à leur empreinte ; uv installe ce que dit `uv.lock`, puis l'image finale n'a plus que
  Python et l'environnement du serveur, sans uv ni sources. Le conteneur est celui de Honear : lecture seule, aucune capacité,
  aucun port publié, 384 Mo et 128 processus au plus.
- **Le frontal a reçu son bloc après le MCP**, le jour de la mise en ligne : avant que le réseau `honear-mcp` existe, il aurait
  fait refuser au script du frontal toute mise en ligne, celle des autres sites comprise.
- **La page d'accueil** n'a ni script ni image : sa politique de sécurité du contenu ne laisse passer que sa feuille de style,
  reconnue à son empreinte, calculée au démarrage. Elle ne nomme pas encore le dépôt public : il n'existe qu'à la phase 7.

Et après le premier essai dans claude.ai :

- **Sans authentification, et c'est voulu** : le serveur ne connaît personne, ne garde rien de personne et n'appelle aucune
  IA payante ; une liste se partage par son lien, qui ne se devine pas. Un OAuth qui accepte tout le monde ne serait qu'un
  décor, avec du code sensible et des jetons en plus. Ce qui protège, ce sont les bornes : la limite par adresse, la part de
  Deezer du MCP, les tailles, le conteneur. Une vraie authentification viendra le jour où le MCP touchera aux données de
  quelqu'un (« mes listes », les scores d'un compte Honear). Dans claude.ai, il faut choisir « No sign-in » à l'ajout.
- **Une liste a 10 pistes au moins**, le moins que Honear joue (sa plus courte face) : la borne vient de son export
  (`PARTIE_DE_HONEAR`). À 5, la première borne, une liste de 6 pistes rendait un lien que le bac refusait (« Trop court pour
  une face »).
- **`jouer_ici` ouvre la partie sans regarder ce que déclare l'appel** : dans claude.ai, il vient d'un client qui ne dit pas
  savoir montrer de fenêtre, alors que claude.ai la montre. Son message ajoute le lien de honear.fr pour un client qui ne la
  montrerait vraiment pas. Les outils de la fenêtre, eux, demandent toujours un client qui la déclare : le modèle n'y joue pas.
- **Un rangement plein fait de la place** au lieu de refuser : il oublie la plus vieille liste que personne n'a jouée. Un
  script qui en crée en boucle n'efface que des listes jamais jouées, et ne bloque personne pendant trente jours.

Et en préparant la vitrine :

- **Le dépôt public reçoit le projet d'un bloc** : `publication/publier.sh` prend l'arbre d'un commit poussé dont la CI est
  verte, vérifie qu'il ne porte ni jeton, ni clé, ni l'adresse IP du VPS (lue dans `~/vps/LISEZMOI.md`, jamais écrite), ni une
  adresse e-mail inconnue, puis le pose en un seul commit sur le dépôt public. Sans `--envoyer`, il ne fait que vérifier. Les
  fausses clés des tests s'appellent « faussecle-… » pour qu'il les reconnaisse.
- **Les captures de la fenêtre** viennent d'un vrai navigateur (Chromium, dans le conteneur Playwright du VPS), avec un hôte
  d'essai fait de l'`AppBridge` d'`@modelcontextprotocol/ext-apps`, converties en WebP de 1600 pixels de large.

Et en écrivant l'assistant d'exploitation :

- **Un second serveur, pas des outils cachés** : `honear-exploitation` tourne en stdio, lancé par Claude Code sur le VPS (ou par
  SSH). Il n'a pas de port. Le serveur public ne lit aucun de ses modules, ni ses réglages ni ses textes, rangés à part ; un test
  suit tout ce que le serveur public importe, de proche en proche, pour le vérifier.
- **Ce qu'il lit, et comment** : les pages `/sante` de Honear et du MCP ; `/statistiques.json`, à la clé ; le certificat que
  chaque site présente sur le port 443, vérifié comme un navigateur ; `git --no-optional-locks status`, `rev-parse` et
  `rev-list @{u}..HEAD` sur les copies de travail (sans récupérer : le minuteur du VPS le fait toutes les cinq minutes) ;
  `gh api …/actions/runs?head_sha=…`. Ni socket Docker, ni sudo : les journaux des conteneurs n'en sont pas.
- **La clé** : copiée une fois par Mateo (`sudo sh deploiement/cle-des-statistiques.sh`) dans
  `~/.config/honear-mcp/statistiques.env`, à lui seul ; relue à chaque demande, envoyée dans l'en-tête `Authorization`, jamais
  rendue ni écrite dans un refus. Un test lui donne une fausse clé et la cherche dans chaque réponse.
- **« Je peux déployer là ? »** : personne ne joue à Honear (une construction occupe la machine du jeu), le MCP n'attend pas
  Deezer, la copie n'a aucun changement, son commit est poussé, et sa CI est verte. Chaque condition qui manque a sa phrase.

## Ce qui attend

- **Phase 3, la suite** : Honear lit déjà les listes (son commit 78ceed2, pas encore en ligne : le lien collé dans le bac, les
  surnoms dans le jugement, l'ordre gardé, 30 appels Deezer par 5 secondes). Il reste à dessiner l'anecdote sur l'écran de
  l'hôte et les écrans du lien ouvert directement, par les planches. Sa recherche avancée, qui ne trouve plus rien, coûte un
  appel pour rien à chaque titre d'une playlist Spotify. Il exportera pour le MCP ses cas de jugement, sa palette et ses
  règles : la ressource `honear://regles` en naîtra.
- **Phase 4, la suite** : le MCP est en ligne (le 16 octobre 2026), Honear lit ses listes, et claude.ai s'y branche en
  connecteur personnalisé, avec « No sign-in » (voir NOTES-TECHNIQUES, « Les journaux »). Reste l'essai des outils dans une
  conversation, par Mateo.
- **Phase 5** : le mini blind test se joue dans claude.ai (essayé par Mateo le 16 octobre).
- **Phase 6, la suite** : la clé des statistiques à copier (Mateo, `sudo sh deploiement/cle-des-statistiques.sh`), et sa
  réponse sur une règle de Claude Code qui interdit de lire `~/.config/honear-mcp/` ; puis
  `claude mcp add honear-exploitation -- uv run --directory ~/honear-mcp honear-exploitation`.
- **Phase 7, la suite** : le README, le kit et le script de publication sont prêts. Restent les captures d'une vraie
  conversation dans claude.ai (Mateo), puis la création du dépôt public `SNZMTO/honear-mcp` et la première publication
  (`sh publication/publier.sh --envoyer`), sur son accord.
