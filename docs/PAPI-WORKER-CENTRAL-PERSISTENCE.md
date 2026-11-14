# Mission 20 — Jour 3/5 : persistance centralisée des PAPI AI WORKERS

## Décision d'architecture
Le dépôt dispose déjà d'un schéma Supabase/PostgreSQL avec RLS, une file de jobs, un registre d'audit et des identités publiques d'agents. Le Jour 3 ajoute une couche additive de persistance métier, sans remplacer ces composants.

## Modèle de données
- `papi_worker_records` conserve le dernier snapshot d'un enregistrement, identifié par le couple domaine + record_id. Domaines autorisés : `platform_candidate`, `human_handoff`, `profitability_result`.
- `papi_worker_event_receipts` conserve les événements acceptés, leur clé d'idempotence, leur contenu et la version produite.
- `papi_audit_events` reçoit en parallèle un événement d'audit pour chaque écriture acceptée.

## Contrat d'écriture
La fonction PostgreSQL `papi_sync_worker_record` effectue dans une seule transaction :
1. validation du domaine et de l'enveloppe ;
2. reconnaissance d'une répétition idempotente ;
3. création ou mise à jour du snapshot sous contrôle de version optimiste ;
4. insertion du reçu d'événement ;
5. insertion de l'événement d'audit.

`p_expected_version = 0` signifie création. Pour une mise à jour, l'appelant doit fournir la version attendue. Un conflit retourne l'état SQL `40001`. Une même clé d'idempotence avec un contenu différent est rejetée en `22023`. Une répétition strictement identique retourne `duplicate=true` sans incrémenter la version.

## Identifiants déterministes
`papi_core.worker_store.build_worker_sync_event` prépare l'enveloppe côté Python. La clé d'idempotence et l'identifiant d'événement sont dérivés de SHA-256 sur le domaine, l'identifiant métier et l'identifiant d'événement source. Les retries du même événement source produisent donc les mêmes identifiants. L'horodatage source doit être stable et inclure un fuseau.

Le module refuse les domaines inconnus, les payloads non JSON, les dates naïves et les champs sensibles connus (mots de passe, OTP, clés privées, jetons, données de carte). Les secrets restent dans le gestionnaire de secrets/backend, jamais dans les snapshots.

## Sécurité
- RLS activé sur les deux nouvelles tables.
- Aucun droit accordé à `public`, `anon` ou `authenticated`.
- Accès de service limité au rôle serveur `service_role`.
- Fonction `SECURITY INVOKER`, sans privilège `SECURITY DEFINER`.
- Aucun accès réseau, worker, notification, inscription ou action financière n'est déclenché par cette livraison.
- Le frontend ne reçoit jamais la clé `service_role`.

## Vérification
Le workflow CI applique le schéma à un PostgreSQL jetable et exécute un test SQL qui couvre création, rejeu idempotent, rejet d'un contenu divergent, mise à jour, conflit de version, audit et permissions.

## Limites
Cette livraison prépare le contrat et les tests. Elle ne modifie aucun projet Supabase hébergé, ne crée aucune migration distante et ne synchronise pas encore les registres locaux automatiquement. Le déploiement du schéma et le raccordement du client backend feront l'objet d'une étape autorisée distincte.
