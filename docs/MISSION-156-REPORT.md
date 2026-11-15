# Mission 156 — Copie hors site des sauvegardes chiffrées

## Livrable
- Module rclone en mode copie, jamais synchronisation destructive.
- Transfère uniquement les archives AES-GCM et leurs manifestes JSON associés.
- Vérifie SHA-256 local avant transfert, puis exécute \`rclone check --one-way --checksum\`.
- Configuration rclone hors dépôt, fichier non symbolique et mode 0600.
- Destination contrôlée, délai borné, erreurs expurgées.
- Runner one-shot séparé, désactivé par défaut ; service Compose profil \`offsite\`.
- Tests simulés de copie, vérification, secret de configuration, fichiers altérés et verrou désactivé.

## Limites
Aucun compte Google Drive/S3 ou remote rclone n'a été connecté. Aucun transfert réel n'a eu lieu. L'opérateur doit créer et sécuriser la configuration rclone, choisir une destination, puis lancer la commande manuellement.
