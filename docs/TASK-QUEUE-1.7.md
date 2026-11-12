# PAPI TASK QUEUE 1.7 — file persistante Supabase

## Portée
Cette étape ajoute une interface Python vers `papi_jobs` et une migration PostgreSQL autonome. PostgreSQL réalise la réservation exclusive avec `FOR UPDATE SKIP LOCKED`; la clé unique `idempotency_key` empêche l'insertion répétée d'un même travail logique.

## Opérations
- `enqueue` : ajoute un job avec handler, charge utile et instantané facultatif de l'identité agent.
- `claim` : réserve atomiquement un job disponible, incrémente les tentatives et retourne un jeton UUID.
- `heartbeat` : prolonge uniquement un bail encore valide appartenant au worker et au jeton exacts.
- `complete` : clôture uniquement le bail correspondant encore valide.
- `fail` : passe le job en reprise avec délai exponentiel borné, ou en échec terminal après le nombre maximal de tentatives.

## Sécurité et limites
- RPC et table réservées à `service_role`; aucun accès `anon` ou `authenticated`.
- Le backend doit authentifier cryptographiquement le worker avant d'appeler la file. Les identifiants transmis ne constituent pas à eux seuls une preuve d'identité.
- Ne jamais exposer la clé Supabase service role au navigateur ou dans le dépôt.
- Aucun handler n'est exécuté par ce module. Pas de boucle worker, pas de lancement de processus, pas d'action externe.
- La politique reste `execution_enabled: false`, budget nul et actions externes désactivées.
- La migration doit être appliquée au projet Supabase avant utilisation réelle. Les tests simulés ne prouvent pas la disponibilité d'une base distante.

## Déploiement
Appliquer `infra/supabase/migrations/003_persistent_job_queue.sql` dans l'éditeur SQL Supabase après le schéma initial et la migration 002. Les définitions de la file doivent rester synchronisées avec `infra/supabase/schema.sql`.
