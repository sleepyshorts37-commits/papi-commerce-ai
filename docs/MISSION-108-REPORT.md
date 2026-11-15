# Mission 108 — Sécurité du registre de quotas et transitions d'état

## Objectif
Renforcer les tests du registre PostgreSQL partagé et de l'adaptateur Cloudflare, sans modifier une base hébergée ni activer de fournisseur.

## Livrables
- Extension de `infra/supabase/tests/013_shared_provider_quota_ledger.sql`.
- Test de non-régression dans `tests/test_image_provider_cloudflare.py`.
- Extension du workflow `.github/workflows/papi-shared-quota-postgres.yml`.
- Vérifications de privilèges, RLS, idempotence, commit, incertitude et libération.

## Couverture SQL ajoutée
- RLS activée sur les deux tables du registre.
- Aucun accès SELECT aux tables pour `anon` et `authenticated`.
- Aucun droit EXECUTE public client sur la RPC de réservation.
- Accès de lecture et EXECUTE attendus pour `service_role`.
- Rejeu idempotent avec intention identique ; rejet d'une intention différente.
- Commit répété avec la même consommation ; rejet d'une consommation modifiée.
- Réservation `uncertain` non libérable ; rapprochement possible par commit.
- Libération idempotente d'une réservation non soumise ; commit d'une réservation libérée rejeté.
- Vérification finale des compteurs consommés/réservés.

## Couverture Python / CI ajoutée
- Teste que les états `uncertain`, `released` et `committed` ne déclenchent jamais un nouvel appel Cloudflare.
- Le workflow lance désormais les tests unitaires de l'adaptateur avant le harnais PostgreSQL et les scénarios concurrents 10/20/50.
- Les chemins Python concernés sont inclus dans les filtres du workflow.

## Références techniques consultées
- Changelog Supabase du 15 novembre 2026 : aucun breaking change Database/Postgres récent identifié comme affectant ces fonctions RPC.
- Documentation Supabase « Database Functions » : privilégier SECURITY INVOKER et restreindre explicitement EXECUTE ; cohérent avec la migration 013 existante.

## Validation réellement effectuée
- Inspection du code source des PR Missions 104 à 107 et de la migration 013.
- Vérification statique des nouveaux scénarios et des étapes CI.
- Aucun PostgreSQL, `psql` ou Docker local disponible dans cette session : les tests SQL et unitaires ne sont pas déclarés exécutés.
- Le workflow CI doit s'exécuter sur la pull request Mission 108 ; aucun résultat vert n'est présumé.
- Aucune migration appliquée, aucun appel Supabase/Cloudflare réel, aucun secret utilisé.

## Limites
- Les tests de privilèges s'exécutent dans le PostgreSQL jetable de CI avec les rôles Supabase simulés ; ils ne remplacent pas un audit du projet Supabase cible.
- Aucun changement du schéma ou des fonctions de production n'a été effectué.
- Les réservations incertaines nécessitent toujours un processus opérationnel de rapprochement avant libération.

## Décision
Tests et garde-fous ajoutés, en attente de leur exécution CI. Pull request proposée en brouillon, non fusionnée.
