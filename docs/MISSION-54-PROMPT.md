# Mission 54 — Prompt

Renforcer la vérification locale du manifeste de transfert de Mission 53. La vérification structurelle d'un manifeste ne suffit pas : les octets présents sur disque doivent être relus et comparés aux empreintes et métadonnées du manifeste.

Livrer une fonction de vérification en lecture seule qui valide strictement le manifeste, les types et tailles, refuse les dossiers symboliques, relit le paquet et la charge utile, reconstruit le manifeste depuis les fichiers et exige une égalité canonique exacte. Refuser fichiers absents, modifiés, non réguliers ou symboliques. N'écrire, n'envoyer, ne consommer aucun nonce et n'importer aucun contenu.

Ajouter tests positifs et négatifs, documentation, roadmap et rapport final. Vérifier les deux jobs CI sur le SHA final. Garder la PR en brouillon ouverte et non fusionnée.
