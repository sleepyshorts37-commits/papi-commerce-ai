# Mission 152 — Création automatique d'une sauvegarde PostgreSQL chiffrée

## Livrable
- Lance \`pg_dump\` en format custom avec TLS obligatoire.
- Lit la connexion depuis le secret serveur \`PAPI_KIDS_DATABASE_URL\`, décompose les champs et transmet les identifiants via l'environnement du processus, jamais dans les arguments CLI.
- Utilise \`--no-password\`, délai borné et sortie d'erreur expurgée.
- Chiffre immédiatement l'archive avec le module AES-256-GCM de la mission 151.
- Le dump en clair est conservé uniquement dans un staging temporaire privé, puis supprimé automatiquement.
- Tests sans connexion réseau : parsing TLS, absence des secrets dans argv, réussite simulée, échec pg_dump expurgé et binaire absent.

## Limites
- Nécessite un runner équipé de \`pg_dump\` et un dossier de sauvegarde monté/isolé.
- Le module ne synchronise pas encore vers un stockage distant et ne planifie pas de sauvegardes.
- Aucun dump réel n'a été exécuté, aucune base externe contactée, aucune dépense ni déploiement.
