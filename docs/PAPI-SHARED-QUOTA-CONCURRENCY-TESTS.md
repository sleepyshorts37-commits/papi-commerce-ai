# Mission 106 — Validation PostgreSQL multi-session du quota partagé

## Objectif
Vérifier que le registre de la migration 013 protège le plafond quotidien lorsque plusieurs workers réservent simultanément depuis des connexions PostgreSQL distinctes.

## Exécution locale
Prérequis : Python 3.10+ et le client PostgreSQL `psql`. Depuis la racine du dépôt :

```bash
export PAPI_TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
python scripts/test_shared_quota_concurrency.py
```

Le port et les identifiants doivent correspondre à TON instance PostgreSQL locale. Le script refuse toute adresse distante : seuls `localhost`, `127.0.0.1` et `::1` sont acceptés. Ne pas fournir l'URL d'un projet Supabase hébergé.

Par défaut, le script applique la migration 013 à la base locale, exécute le test SQL de contrat, puis lance les scénarios de concurrence. Si la migration est déjà appliquée :

```bash
python scripts/test_shared_quota_concurrency.py --skip-migration
```

## Scénarios et résultat attendu
- 10 agents : 10 réservations acceptées, quota 100/100.
- 20 agents : 10 acceptées, 10 refusées.
- 50 agents : 10 acceptées, 40 refusées.

Chaque agent utilise un processus `psql` distinct, donc une session PostgreSQL distincte. Chaque réservation coûte 10 unités et le plafond est fixé à 100. Après chaque vague, le script vérifie directement le compartiment : `reserved_units=100`, `consumed_units=0`, `daily_limit=100`.

Le test SQL de contrat existant vérifie également l'idempotence, le refus du dépassement, la conversion réservation/consommation, et le maintien d'une réservation incertaine.

## Sécurité et limites
- Base locale uniquement ; aucune connexion réseau applicative vers Cloudflare.
- Aucun secret n'est écrit dans le dépôt. L'URL de test est fournie uniquement via l'environnement.
- Le script applique la migration 013 sur la base locale, sauf option `--skip-migration`.
- Les scénarios utilisent une date fixe en 2099 et des comptes de test isolés.
- Ce test démontre le comportement de la fonction SQL dans PostgreSQL local ; il ne valide pas les quotas Cloudflare réels, la latence Supabase hébergée, ni la configuration réseau/permissions d'un projet de production.
- Le script n'a pas valeur de test CI tant qu'il n'est pas exécuté dans un environnement PostgreSQL.

