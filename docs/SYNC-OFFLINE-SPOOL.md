# Échange hors ligne des paquets de synchronisation

## But et périmètre
Mission 43 ajoute un spool local de fichiers .papisync pour déplacer manuellement un paquet référentiel entre environnements. Le spool ne contacte aucun réseau, ne transporte aucun contenu de mémoire/message et ne déclenche aucun import.

## Écriture et lecture
- write_sync_package(bundle, approval, spool_dir) valide le paquet et la cohérence de l'approbation, puis écrit un JSON canonique versionné.
- Le nom de fichier est l'empreinte SHA-256 de l'enveloppe complète.
- Écriture temporaire, fsync, création atomique sans écrasement et permissions dossier/fichier 0700/0600.
- Taille maximale : 2 Mio.
- read_sync_package(path) refuse liens symboliques, fichiers non réguliers, noms non conformes, JSON ambigu avec clés dupliquées, versions inconnues, empreintes altérées et approbations ne correspondant pas au paquet.

## Séparation des garanties
La lecture valide la forme et les empreintes, mais ne vérifie pas la signature Ed25519, ne consomme aucun nonce, n'établit pas la confiance dans le propriétaire et ne marque pas le paquet comme autorisé. L'appelant doit ensuite utiliser le vérificateur d'approbation et le registre atomique de Mission 42 sur l'instance destinataire. L'import du contenu demeure manuel et hors périmètre.

## Sécurité opérationnelle
- Utiliser un répertoire privé contrôlé par l'utilisateur, sur un disque local.
- Ne jamais déposer de clé privée, secret ou donnée client dans le spool.
- Transférer les fichiers manuellement par un canal autorisé; vérifier l'identité de la destination.
- Conserver les journaux et reçus selon la politique de rétention.
- Ne pas ouvrir un paquet reçu depuis une source non fiable avec des outils qui exécutent son contenu.

## Limites
Mono-instance et système de fichiers local; pas de chiffrement au repos, transport réseau, réplication, verrou distribué, import de mémoire/chat, worker ou scheduler. SHA-256 détecte l'altération, pas l'auteur. La signature Ed25519 doit être vérifiée séparément.
