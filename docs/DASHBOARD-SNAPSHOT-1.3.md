# PAPI COMMAND CENTER 1.3 — snapshot Supabase cohérent

## Fonctionnement

La commande distante utilise désormais la RPC SQL `papi_get_dashboard_snapshot` pour lire les tâches et le journal d'audit dans un seul appel. La fonction est déclarée `STABLE`, `SECURITY INVOKER`, et ne contient que des lectures. Les requêtes internes partagent ainsi le snapshot MVCC de la requête appelante.

La RPC retourne :
- les tâches avec `id`, `task` et `version` ;
- les événements d'audit nécessaires à l'historique ;
- deux indicateurs de troncature ;
- l'identifiant de cohérence `single_statement_snapshot`.

Les limites sont bornées entre 1 et 20 000 lignes pour chaque ensemble. Si une limite est dépassée, le client refuse de présenter un tableau de bord partiel.

## Déploiement SQL

Appliquer `infra/supabase/migrations/002_dashboard_snapshot.sql` dans le projet Supabase, ou réexécuter le schéma consolidé `infra/supabase/schema.sql`.

La fonction est révocable pour `public`, `anon` et `authenticated`, et son exécution est accordée à `service_role`. Elle est `SECURITY INVOKER` : elle ne contourne pas les permissions de l'appelant. Les clés privées ne sont pas concernées et aucun secret n'est stocké dans le dépôt.

## Limites

- L'appel PostgREST utilise HTTP POST pour invoquer la fonction, mais la fonction SQL est déclarée `STABLE` et n'effectue aucune écriture.
- Le précontrôle de la version 1.2 reste un contrôle préalable ; la RPC peut encore échouer si le schéma n'a pas été migré ou si les droits sont insuffisants.
- Les tests utilisent des réponses simulées. Aucune base Supabase réelle n'a été modifiée ni testée.
- Aucun worker n'est démarré et aucun agent n'est activé.
