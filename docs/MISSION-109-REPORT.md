# Mission 109 — Rapprochement des réservations de quota incertaines

## Objectif
Donner à PAPI un moyen contrôlé d'identifier les réservations ouvertes, les anomalies de comptabilité et les cas qui nécessitent une enquête humaine, sans libération ou commit automatique.

## Livrables
- `scripts/audit_shared_quota_ledger.sql` : audit SQL en lecture seule.
- `docs/PAPI-QUOTA-RECONCILIATION-RUNBOOK.md` : classification, procédure et interdictions.
- `scripts/test_shared_quota_concurrency.py` : exécute l'audit dans l'environnement PostgreSQL local de CI.
- `.github/workflows/papi-shared-quota-postgres.yml` : déclenchement sur les changements de l'audit.

## Contrôles
- Compare `reserved_units` à la somme des réservations `reserved` et `uncertain`.
- Détecte un dépassement du plafond journalier.
- Repère les réservations ouvertes de plus d'une heure et de plus de 24 heures.
- Fournit une file d'investigation au niveau réservation.
- Ne modifie aucune donnée et n'appelle aucun fournisseur.

## Gouvernance
- Un timeout ou une erreur réseau ne prouve jamais que Cloudflare n'a pas exécuté la requête.
- Aucune libération automatique par ancienneté.
- Aucune nouvelle génération pour « tester » une réservation incertaine.
- La correction exige des preuves externes et une validation humaine.
- Les clés service-role restent exclusivement côté serveur.

## Documentation officielle vérifiée
- Changelog Supabase consulté au 15 novembre 2026 : les breaking changes récents identifiés concernent notamment Supabase CLI v3 (4 novembre) et les ciphers TLS 1.2 (10 novembre). Aucun ne change directement le schéma SQL de cette mission.
- Documentation Supabase consultée via `search_docs` : privilèges Postgres et tests RLS. Le registre reste en SECURITY INVOKER, avec privilèges explicites et tables backend-only.

## Validation réellement effectuée
- Inspection de la migration 013, de l'adaptateur et du harnais PostgreSQL.
- Contrôle statique de la requête SQL : lecture uniquement (`SELECT`/CTE), aucune instruction DML/DDL.
- Le harnais lance désormais la requête d'audit après le test de contrat.
- Aucun test PostgreSQL local exécuté ; pas de `psql`, PostgreSQL ni Docker dans l'environnement.
- Aucune exécution CI confirmée à la clôture.
- Aucun projet Supabase hébergé consulté ou modifié ; aucun secret utilisé.

## Limites assumées
- Pas de table append-only dédiée aux événements de rapprochement.
- Pas de RPC de correction à double approbation.
- Le CLI Supabase n'est pas disponible dans l'environnement ; conformément aux règles Supabase, aucune migration n'a été inventée à la main. Aucun identifiant de projet n'autorise une opération distante.
- Les journaux Cloudflare et les preuves de consommation doivent être vérifiés par un opérateur autorisé.

## Décision
Le dispositif de détection et le runbook sont livrés. La résolution reste volontairement manuelle jusqu'à la mise en place d'un journal d'audit append-only et d'un circuit d'approbation contrôlé. PR en brouillon, non fusionnée.
