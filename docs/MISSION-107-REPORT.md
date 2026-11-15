# Mission 107 — Intégration continue PostgreSQL

## Objectif
Rendre les tests de la migration 013 reproductibles dans GitHub Actions, sans dépendre d'un projet Supabase hébergé.

## Livrable
- `.github/workflows/papi-shared-quota-postgres.yml` : service PostgreSQL 16 jetable, rôles `anon`, `authenticated` et `service_role`, puis exécution du harnais Mission 106.
- Déclenchement sur les pushes de la branche Mission 107, les pull requests touchant les fichiers concernés et le lancement manuel.

## Séquence CI
1. Démarrage d'un conteneur PostgreSQL 16 avec healthcheck.
2. Création des rôles compatibles avec les GRANT/REVOKE de la migration.
3. Exécution du harnais : migration 013, test SQL de contrat, scénarios multi-session 10/20/50.
4. Vérification de l'état final des compteurs de quotas.

## Validation et limites
- Environnement local de cette session : ni `psql`, ni serveur PostgreSQL, ni Docker détectés ; les tests n'ont donc pas pu être exécutés localement.
- Le workflow a été ajouté à la branche et doit produire le premier résultat CI après son déclenchement GitHub Actions. Aucun succès n'est présumé.
- Le workflow utilise une base éphémère de CI ; aucun secret Supabase, jeton Cloudflare ou projet hébergé n'est utilisé.
- Le test vérifie les RPC SQL et la concurrence PostgreSQL ; il ne valide pas l'accès réseau PostgREST ni les quotas réels Cloudflare.
