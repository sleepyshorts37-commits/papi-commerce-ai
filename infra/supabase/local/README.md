# Environnement PostgreSQL jetable pour les contrats Supabase

Ce compose fournit PostgreSQL 16 et PostgREST pour vérifier les migrations, contraintes, RLS, privilèges, triggers et contrats HTTP REST PAPI. Il ne lance pas Supabase Auth, Storage, Realtime ni l'API Gateway/Kong : il valide un JWT HS256 local à PostgREST, pas l'émission/validation des JWT par Supabase Auth.

## Prérequis

- Docker Engine et le plugin Docker Compose v2.
- Client psql PostgreSQL 16+ sur la machine hôte.

## Démarrage et application

Depuis la racine du dépôt :

```sh
docker compose -f infra/supabase/local/docker-compose.yml up -d --wait
export PGPASSWORD=papi_local_only_password
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -f infra/supabase/schema.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -f infra/supabase/migrations/004_shared_collaboration.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -f infra/supabase/migrations/004_shared_collaboration.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -f infra/supabase/migrations/005_collaboration_pagination_idempotency.sql
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -f infra/supabase/migrations/005_collaboration_pagination_idempotency.sql
```

Les doubles applications vérifient le caractère ré-exécutable des migrations. Pour repartir de zéro, supprimer le conteneur puis le recréer :

```sh
docker compose -f infra/supabase/local/docker-compose.yml down
docker compose -f infra/supabase/local/docker-compose.yml up -d --wait
```

## Contrat HTTP PostgREST réel\n\nLe service REST est publié uniquement sur `127.0.0.1:55433`. Le test Python crée un JWT HS256 local avec le rôle `service_role`, insère un message, vérifie le filtre serveur du destinataire puis confirme que la mutation d'un message append-only est refusée. Le secret JWT et le mot de passe PostgreSQL sont des valeurs de test locales uniquement. Le test refuse toute URL REST hors loopback.\n\nCe test ne valide pas Supabase Auth, les politiques JWT de l'API Gateway Supabase, ni les services Storage/Realtime. Il ne doit jamais être pointé vers un projet hébergé.\n\n## Contrôles rapides

```sh
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -c "select to_regclass('public.papi_memory_events'), to_regclass('public.papi_chat_messages');"
psql -h 127.0.0.1 -p 55432 -U postgres -d papi_contract_test -v ON_ERROR_STOP=1 -c "select has_table_privilege('service_role', 'public.papi_memory_events', 'insert') as service_can_insert, has_table_privilege('anon', 'public.papi_memory_events', 'select') as anon_can_read;"
```

Attendu : les deux tables existent, service_can_insert vaut true et anon_can_read vaut false.

## Sécurité et limites

- Base éphémère en tmpfs, port publié uniquement sur loopback.
- Mot de passe fixe de test exclusivement local ; aucune clé Supabase réelle.
- Ne pas y importer de données client ni de mémoire réelle.
- Aucune connexion à un projet hébergé, aucune synchronisation inter-instance.
- Le prochain niveau de validation doit utiliser la CLI Supabase et ses services locaux, puis un projet de test isolé uniquement après autorisation explicite.
