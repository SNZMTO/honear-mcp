# Le MCP de Honear, pour mateosan.fr

De quoi présenter le projet sur la vitrine de mateosan.fr. Aucun nombre qui change d'un commit à l'autre.

**Titre** : Le MCP de Honear

**Accroche** : Les playlists de blind test qu'aucun bac ne propose, faites par ton assistant, jouées sur honear.fr ou dans la
conversation.

**Résumé** : Un serveur MCP qui laisse un assistant (Claude, ChatGPT…) préparer une playlist de blind test sur n'importe quel
thème, une occasion ou une capture d'écran. L'assistant choisit les titres ; le serveur les vérifie chez Deezer, écarte ce qui
jouerait mal et enregistre la liste pour Honear, ou la fait jouer tout de suite dans une fenêtre de la conversation. Il
n'appelle lui-même aucune IA.

**Points forts**

- **Aucune IA payante** : c'est l'assistant de la personne qui réfléchit ; le serveur vérifie, enregistre, sert et juge.
- **Un blind test dans la conversation** : une fenêtre MCP Apps aux couleurs de Honear, dont les réponses n'atteignent jamais
  le modèle avant la révélation.
- **Une seule vérité pour le jugement** : celui du jeu, porté en Python et vérifié contre une table que le jeu exporte lui-même.
- **Une architecture qui se vérifie seule** : des couches et des règles de code tenues par un test, et un faux Deezer.
- **En production, sobrement** : conteneur durci, aucune adresse IP écrite, un registre RGPD, Deezer partagé avec le jeu.

**La part de Claude Code** : écrit avec Claude Code, phase après phase, dans le cadre que j'ai posé : le cahier de lancement, les
six décisions, les règles du code, et chaque mise en ligne.

**Liens** : [le dépôt](https://github.com/SNZMTO/honear-mcp), [mcp.honear.fr](https://mcp.honear.fr)

**Captures** (WebP ; celles de la fenêtre font 1600 pixels de large, celle de claude.ai 810)

- [`.github/captures/mini-blind-test-ecoute.webp`](../.github/captures/mini-blind-test-ecoute.webp) : « Le mini blind test de
  Honear dans une conversation : le disque tourne pendant l'extrait, et une réponse vient d'être jugée juste. »
- [`.github/captures/mini-blind-test-revelation.webp`](../.github/captures/mini-blind-test-revelation.webp) : « La révélation
  d'une piste : « Yellow » de Coldplay, sa pochette sur l'étiquette du disque, son anecdote et le score. »
- [`.github/captures/dans-claude-ai.webp`](../.github/captures/dans-claude-ai.webp) : « Dans claude.ai : on demande à jouer
  la liste, et la fenêtre du mini blind test s'ouvre dans la conversation, sur « Piste 1 sur 5 ». »
