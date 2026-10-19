# Notes techniques

## Deezer

Le MCP lit l'API publique de Deezer (https://api.deezer.com), sans compte ni clé, comme Honear.

### Le budget, partagé avec Honear

Deezer admet 50 appels par 5 secondes et par adresse IP. Sur le VPS, Honear et le MCP sortent par la même : le MCP s'en
autorise 10 (`DEEZER.par_fenetre`), et Honear passe de 40 à 30 avant que le MCP soit en ligne, ce qui laisse 10 de marge.
Un seul objet `Deezer` sert tout le serveur : la limite vaut quel que soit le nombre de clients.

- **La limite** est une fenêtre glissante (`reseau/debit.py`), celle de Honear : on oublie les appels sortis de la fenêtre, et
  s'il n'y a plus de place, on attend que le plus ancien en sorte.
- **Quand Deezer dit qu'on va trop vite** (son code 4), on attend une fenêtre et on redemande : 3 essais en tout.
- **Une réponse qui tarde** est abandonnée au bout de 8 secondes.
- **La file** : au-delà de 40 appels qui attendent leur tour, on n'en prend plus, et l'outil dit de réessayer dans une
  minute. Mieux vaut un refus tout de suite qu'une attente qui affame tout le monde.
- **Le cache** : une recherche est gardée une heure (2 000 au plus). Un lot redemandé, ou corrigé d'un titre, ne rappelle
  Deezer que pour ce qui a changé.

### La recherche d'un titre

Un appel par titre : `/search/track?q=<artiste> <titre>&limit=10`, le titre sans son habillage (« - Remastered 2011 », ce qui
est entre parenthèses). La recherche avancée (`artist:"…" track:"…"`) ne trouvait plus rien le 16 octobre 2026, pas même
« Daft Punk, One More Time » : la recherche en vrac la remplace, et c'est la comparaison des noms qui trie.

- **Trouvé** : une piste a le nom et l'artiste cherchés, aux accents, à la ponctuation et à l'habillage près, ou l'un
  contient l'autre (« Gims » et « GIMS », « Maître Gims »). C'est la règle qu'avait Honear pour les playlists Spotify
  (`laBonnePiste`), partie avec elles le 16 octobre 2026. Parmi les versions, celle qui n'a pas de drapeau, la plus populaire
  (`rank`).
- **Ambigu** : aucune piste ne l'est, mais certaines ressemblent assez au titre cherché (0,6 sur 1, artiste et titre ensemble,
  par `difflib`) : les 4 plus proches, à égalité la plus populaire d'abord. Le modèle choisit par l'identifiant Deezer.
- **Introuvable** : rien ne ressemble assez.

Le titre rendu est celui que Honear montre et attend (`titre_montre`, d'après `titreSansEdition`) : sans son invité ni ce
qui dit son édition ; le titre complet de Deezer l'accompagne.

### Les drapeaux

| Drapeau | Ce qui le lève |
|---|---|
| `sans_extrait` | pas de lien d'extrait en `https://`, ou une piste que Deezer ne laisse pas lire |
| `live` | « live », « en concert », « en public », « en direct », « unplugged », dans le titre ou sa version |
| `remix` | « remix », « rmx », « rework », « bootleg », « mashup », « mix » (sauf « original mix »), « slowed », « sped up », « nightcore » |
| `karaoke` | « karaoké », « backing track », « in the style of », « made famous by », « originally performed by », titre ou artiste |
| `reprise` | « cover », « tribute », « hommage », « reprise », titre ou artiste |
| `doublon` | la même piste Deezer, trouvée plus haut dans le même lot |

### Les réponses enregistrées

Les tests ne touchent jamais au réseau (`tests/conftest.py` coupe toute connexion). Le faux Deezer (`tests/faux_deezer.py`)
rejoue les réponses de `tests/deezer/`, un fichier par adresse, enregistrées telles quelles chez le vrai le 16 octobre 2026.
Une adresse qu'il ne connaît pas fait échouer le test. Pour en enregistrer une autre, une fois, quand personne ne joue :

```
uv run python -c 'import json, sys, urllib.request
from honear_mcp.sources.deezer import adresse_de_recherche
a = adresse_de_recherche(sys.argv[1], sys.argv[2])
r = json.load(urllib.request.urlopen("https://api.deezer.com" + a, timeout=8))
print(json.dumps({"adresse": a, "reponse": r}, ensure_ascii=False, indent=1))' "Artiste" "Titre" > tests/deezer/artiste-titre.json
```

## Les listes

### Ce que Honear lit

`GET http://<le MCP>:8791/listes/{id}` rend la liste en JSON, ou 404 si elle n'existe pas ou plus. Ce port ne passe pas par
le frontal : Honear le joint sur le réseau Docker `honear-listes`. Lire une liste, c'est la jouer : elle revit 30 jours.

```json
{
  "id": "iTRYNDDqk3g0zBoA",
  "nom": "Une couleur dans le titre",
  "dans_l_ordre": true,
  "pistes": [
    {
      "deezer": 89629797,
      "titre": "Blue (Da Ba Dee)",
      "artiste": "Eiffel 65",
      "rang": 873407,
      "surnoms": { "artiste": [], "titre": ["Da Ba Dee"] },
      "anecdote": ""
    }
  ],
  "jusqua": 1794787200.0
}
```

- `dans_l_ordre` : jouer les pistes dans cet ordre (la difficulté monte) ; sinon, Honear les mélange comme une playlist.
- `deezer` : Honear relit chaque piste chez Deezer par son identifiant (`/track/{id}`), pour un extrait frais ; `titre` et
  `artiste` sont ceux de Deezer, tels que Honear les montre et les attend.
- `surnoms` : d'autres réponses justes, en plus de celles que le jugement de Honear accepte déjà. 3 au plus par partie, 40
  signes chacun.
- `anecdote` : une phrase de 160 signes au plus, montrée à la révélation ; vide quand le modèle n'en a pas donné.
- `jusqua` : quand elle sera oubliée, en secondes depuis 1970.

Le modèle Pydantic `Liste` (`regles/liste.py`) est ce contrat : il écrit le fichier, et c'est lui que la route rend.

### Le rangement

Un fichier par liste, `<id>.json`, dans le dossier de `HONEAR_MCP_LISTES` (`/var/lib/honear-mcp/listes` dans le conteneur).
Une écriture passe par `.<id>.tmp`, vidé sur le disque (`fsync`), puis mis à sa place d'un coup, et le dossier vidé à son
tour : un arrêt brutal laisse l'ancienne liste ou la nouvelle. Les restes d'une écriture interrompue et les listes oubliées
s'effacent au démarrage et à chaque création. 2 000 listes vivent à la fois au plus ; au-delà, une nouvelle prend la place de
la plus vieille que personne n'a jouée (sur Honear ou dans la fenêtre du mini blind test : `jouee` dans son fichier), et si
toutes l'ont été, de celle qui s'oublierait la première. Un script qui crée des listes en boucle n'efface donc que des listes
jamais jouées, et n'empêche personne d'en créer : une limite par adresse n'y suffirait pas, tous les utilisateurs de claude.ai
arrivant par les mêmes adresses d'Anthropic.

L'identifiant vient de `secrets.token_urlsafe(12)` : 96 bits, 16 signes. Il n'est qu'un nom de fichier : tout ce qui n'est
pas lettre, chiffre, « - » ou « _ » ne désigne aucune liste.

### Le départage

Un titre demandé sans identifiant Deezer est cherché. S'il est ambigu, un résolveur du SDK (`Resolve`, dans
`outils/departage.py`) pose la question avant que l'outil commence : un formulaire d'élicitation, un champ par titre ambigu,
dont les choix (`oneOf`, un identifiant et son nom) sont ses candidats et « aucune ». Sur le protocole 2026-07-28, la question
part dans la réponse (`input_required`) et revient avec le nouvel essai du client ; le résolveur repasse, refait les mêmes
recherches (gardées), et le SDK y reconnaît la réponse. Sur l'ancien protocole, c'est une requête du serveur au client.

Pas de question quand le client n'a pas dit savoir montrer un formulaire, ni au-delà de 5 titres ambigus : l'outil refuse
alors en rendant les candidats de chacun, et le modèle demande lui-même.

## Le jugement de Honear, porté

`regles/jugement.py` (normaliser, compter les fautes, entendre, juger) et `regles/parties.py` (la saisie libre, partie par
partie) sont le portage de `src/regles/jugement.ts` et de `src/regles/modes/libre.ts`. Leurs réglages viennent de Honear
(`ressources/honear.py`). Le portage est jugé contre `tests/jugement-de-honear.json` : pour chaque saisie, sa forme normalisée,
ce qu'on en entend, et le verdict du jeu ; pour chaque saisie libre, les parties trouvées. Pour refaire la table après un
changement du jeu : `npm run exporter-pour-le-mcp -- ~/honear-mcp` dans Honear, puis les tests ici.

Il sert déjà à `creer_liste`, qui oublie les surnoms que Honear accepte sans eux ; il servira au mini blind test.

## Le mini blind test (MCP Apps)

L'extension MCP Apps du SDK (`mcp.server.apps`) : `jouer_ici` porte `_meta.ui.resourceUri = ui://honear/mini-blind-test.html`,
que l'hôte lit (`resources/read`, en `text/html;profile=mcp-app`) et affiche dans un iframe isolé ; il lui passe le résultat de
`jouer_ici` (`ui/notifications/tool-result`). La fenêtre appelle ensuite `mini_piste`, `mini_repondre` et `mini_reveler`, que
l'hôte relaie au serveur ; leur `_meta.ui.visibility` vaut `["app"]`, et ils refusent un client qui n'a pas annoncé
l'extension `io.modelcontextprotocol/ui` avec ce type de page. À la fin, la fenêtre dit au modèle le score et les pistes
(`ui/update-model-context`).

- **La politique de contenu** (`_meta.ui.csp.resourceDomains`) : `https://mcp.honear.fr` (les polices) et `https://*.dzcdn.net`
  (les extraits et les pochettes de Deezer) ; rien d'autre, pas de `connectDomains`.
- **La page** : un gabarit (`ressources/mini-blind-test.html`) où le serveur pose, au démarrage, la palette de Honear (des
  variables CSS), l'adresse de ses polices et le script de `interface/`, en un seul fichier.
- **Les polices** : `GET /polices/<fichier>`, les trois `.woff2` de Honear, avec `Access-Control-Allow-Origin: *` (une police
  se charge en CORS, et la fenêtre n'a pas notre origine), gardées un an.
- **La fenêtre** (`interface/src/mini.ts`) : la classe `App` de `@modelcontextprotocol/ext-apps` (l'entrée `app-with-deps`, qui
  embarque ses dépendances), ses textes dans `interface/src/textes.ts`. `npm run construire` (dans `interface/`) vérifie ses
  types et écrit le script.

## Le protocole

- **Le SDK** : `mcp` 2.3.0, `MCPServer`. Il sert la version 2026-07-28 du protocole (sans session ni poignée de main), et les
  clients plus anciens (2025-11-25 et avant), qui ouvrent une session : 200 au plus, oubliées après 5 minutes sans nouvelles.
  Une adresse en ouvre 5 au plus par 10 minutes (au-delà : 429 et `Retry-After`) : sans cette borne, un seul client prenait
  les 200 places, et le SDK répondait « Too many open sessions » (503) à tout le monde. Seul compte un POST sans session de
  l'ancien protocole (un `initialize`), reconnu à ses en-têtes ; le protocole 2026-07-28 n'y compte pas. Le prix : la
  vérification de claude.ai, à l'ajout du connecteur, est une poignée de main de l'ancien protocole partie des serveurs
  d'Anthropic (voir « Les journaux ») ; si elle vient toujours de la même adresse, un sixième ajout en dix minutes attend.
- **Le transport** : Streamable HTTP sur `/mcp`, dans une application Starlette servie par uvicorn. Chaque adresse IP envoie
  120 requêtes par minute au plus (au-delà : 429 et `Retry-After`) ; l'adresse est celle que le frontal donne. Le SDK ne répond qu'aux
  noms qu'on lui donne (l'en-tête `Host` : `mcp.honear.fr`, et la machine elle-même) et refuse une page d'un autre site
  (l'en-tête `Origin`) : contre le DNS rebinding.
- **Les sorties** : chaque outil rend un modèle Pydantic. Le SDK en tire le schéma de sortie, le `structuredContent`, et le
  même objet en JSON dans `content`, que lit le modèle.
- **Les refus** : un refus prévu (`ToolError`) arrive au modèle comme un résultat en erreur, avec sa phrase, que le SDK fait
  précéder de « Error executing tool <nom>: ».
- **La progression** : `chercher_titres` et `creer_liste` disent où ils en sont après chaque titre
  (`notifications/progress`), pour les clients qui la demandent.

## `/sante`

`GET /sante` rend `{"deezer_en_attente": 0, "recherches_gardees": 0, "listes": 0}` : de quoi vérifier une mise en ligne d'un
coup d'œil, voir si quelqu'un attend Deezer en ce moment, et combien de listes sont rangées.

## L'assistant d'exploitation

Un serveur MCP en stdio, `honear-exploitation`, avec ses outils (`etat`, `statistiques`, `certificats`, `ci`,
`peut_on_deployer`) et un prompt (`bilan`), tous en lecture. Il appelle par trois portes qu'on lui donne, et que les tests
remplacent : un client HTTP (les pages de Honear et du MCP), une commande (`git`, `gh`, lancées sans shell, et qui ne font que
lire) et un lecteur de certificats (une connexion TLS au port 443, dont on lit `notAfter`). Ce qui ne répond pas rend rien,
sans faire échouer le reste : `mcp: null` tant que le MCP n'est pas en ligne, un certificat sans échéance « à regarder ».

Les statistiques : `/statistiques.json` de Honear, avec `Authorization: Bearer <clé>`. On en rend, pour une période (un jour, une
semaine, un mois, tout), la somme des compteurs jour par jour, et ce que Honear classe déjà : les recherches du bac, les
playlists choisies, les titres les plus joués et les plus durs. Ce sont des compteurs : rien de personne.

## Les journaux

Le serveur écrit sur sa sortie ce qu'uvicorn dit de sa vie (un démarrage, un arrêt), et les avertissements du SDK (une session
refusée faute de place). Le journal des requêtes d'uvicorn est coupé (il garderait l'adresse IP de chaque client) ; ceux de
httpx2 et du SDK n'écrivent que leurs avertissements (`regler_les_journaux`) : chaque adresse demandée à Deezer porte ce que
quelqu'un cherche, et le SDK écrivait, à INFO, le texte d'un refus (ceux de `creer_liste` citent les titres demandés),
l'adresse d'une ressource lue (l'identifiant d'une liste) et l'identifiant de chaque session. Reste la trace d'une erreur
inattendue, qu'il écrit toujours : elle peut citer l'adresse de la ressource en cause.

À la place, le nôtre (`serveurs/journal.py`) écrit une ligne par requête au MCP, c'est-à-dire tout sauf la page d'accueil,
`/sante` et les polices : la méthode HTTP, le chemin, le code de la réponse, la méthode MCP lue dans le corps (ses 16 premiers
Ko), l'outil appelé, le genre de ressource lue (`ui://honear`, `honear://listes`, sans l'identifiant), le client qui se
présente et ce qu'il dit savoir faire (ses capacités ; pour une extension, ses types MIME), la version du protocole, si une
session est donnée, et les en-têtes Origin, Accept et User-Agent. Ni l'adresse, ni les arguments d'un outil. Il sert à voir ce que fait un client qui n'arrive pas à se brancher (claude.ai ne dit que « Couldn't register… ») :
`sudo docker logs honear-mcp-mcp-1 2>&1 | grep "^http="`. Les journaux des conteneurs vont à journald, qui les fait tourner.

Ce qu'il a montré de claude.ai, le 16 octobre 2026, à l'ajout du connecteur :

- **La vérification** part des serveurs d'Anthropic (`python-httpx`) : une poignée de main de l'ancien protocole (2025-11-25),
  qui réussit. Avec l'authentification par défaut, claude.ai cherche quand même un serveur OAuth : les trois adresses
  `/.well-known/…` (404), puis `POST /register` (404), et il s'arrête sur « Couldn't register with … sign-in service ». Avec
  « No sign-in », il passe.
- **Ensuite**, la conversation (`Claude-User`) parle le protocole 2026-07-28, sans session : `server/discover`, puis
  `tools/list`, `prompts/list` et `resources/list`.
- **Claude Code**, branché au même connecteur (une session sur claude.ai/code), se présente `claude-code/2.1.301`, avec le même
  User-Agent, et ne déclare qu'`elicitation` et `roots` : pas MCP Apps, donc `jouer_ici` lui rend le lien de honear.fr. C'est
  ce qu'a reçu le premier essai de Mateo.
- **Dans une conversation claude.ai**, c'est pareil pour l'appel de `jouer_ici` : il vient d'un client `claude-code/2.1.301`,
  sans MCP Apps. Pourtant claude.ai montre la fenêtre, qui se branche ensuite avec un autre client, `claude-ai/0.1.0`, qui
  déclare `io.modelcontextprotocol/ui` et `text/html;profile=mcp-app`. `jouer_ici` ouvre donc la partie sans regarder ce que
  déclare l'appel (son message ajoute le lien de honear.fr, au cas où la fenêtre ne s'affiche pas) ; seuls les outils de la
  fenêtre (`mini_piste`, `mini_repondre`, `mini_reveler`) demandent un client qui la déclare. Vérifié le 16 octobre : les
  appels de la fenêtre arrivent bien de `claude-ai/0.1.0`, qui la déclare, et la partie se joue dans claude.ai.
