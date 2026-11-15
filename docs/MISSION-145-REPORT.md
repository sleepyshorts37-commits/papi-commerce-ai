# Mission 145 — Service worker supervisé et connexion PostgreSQL serveur

## Livrables
- Boucle de traitement bornée par cycles et taille de lot, polling différencié actif/inactif, arrêt coopératif.
- Entrée CLI \`python -m papi_core.papi_kids_worker_service\`.
- Activation explicite uniquement via \`PAPI_KIDS_WORKER_ENABLED=true\`.
- Identifiant unique \`PAPI_KIDS_WORKER_ID\`, volume privé \`PAPI_KIDS_PRIVATE_STORAGE_DIR\`, URL PostgreSQL \`PAPI_KIDS_DATABASE_URL\`.
- Factory DB-API avec validation PostgreSQL/TLS, refus localhost en production, secret conservé uniquement dans l'environnement serveur.
- Gestion SIGTERM/SIGINT pour arrêt propre.
- Dépendance psycopg ajoutée ; tests hors réseau pour désactivation, polling, arrêt, URL TLS et factory injectée.

## Sécurité / coûts
- Le worker exécute uniquement l'analyse structurelle locale déjà présente.
- \`provider_calls=0\`, \`ai_calls=0\` ; aucun appel image ou LLM.
- Le worker reste désactivé par défaut ; aucun service hébergé ou déployé.
- Aucun secret n'est ajouté au dépôt.
