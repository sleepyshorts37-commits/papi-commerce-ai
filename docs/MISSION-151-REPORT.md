# Mission 151 — Chiffrement et vérification des sauvegardes PostgreSQL

## Livrable
- Chiffrement en flux des archives \`pg_dump --format=custom\` avec AES-256-GCM.
- Clé 32 octets encodée Base64, lue exclusivement depuis le secret serveur \`PAPI_KIDS_BACKUP_KEY_B64\`.
- Identifiant de clé pour rotation ; nonce aléatoire et données authentifiées (AEAD).
- Manifeste privé avec SHA-256 source/chiffré, date UTC, format, taille et identifiant de clé.
- Déchiffrement de vérification, authentification GCM et contrôle du hash et de l'en-tête PGDMP.
- Écritures atomiques et permissions 0600.
- Tests mauvais secret, altération du chiffré, archive invalide et aller-retour complet.

## Limites opérationnelles
- Ce module chiffre une archive pg_dump déjà créée ; il ne se connecte pas à PostgreSQL et n'exécute aucun dump réel.
- Il ne téléverse pas vers un stockage hors site et n'effectue pas de restauration DB. L'opérateur doit conserver une copie chiffrée hors site et effectuer régulièrement une restauration de test avec \`pg_restore\` dans une base isolée.
- Aucun secret réel, aucune dépense, aucun accès externe ni déploiement.
