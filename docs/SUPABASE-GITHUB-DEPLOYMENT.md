# Déploiement Supabase depuis GitHub

Le dépôt contient maintenant une migration au format attendu par Supabase CLI :

`supabase/migrations/20261112000000_initial_papi_schema.sql`

## Ce que fait cette migration

Elle crée les tables PAPI (missions, audit, file d'exécution, clés publiques des agents et nonces), les index et les fonctions RPC transactionnelles. Elle active RLS et retire les droits des rôles `anon` et `authenticated`; les opérations serveur sont prévues avec `service_role`.

## Déploiement

1. Vérifier dans Supabase Dashboard que le dépôt GitHub `sleepyshorts37-commits/papi-commerce-ai` est bien lié au bon projet Supabase.
2. Vérifier que la branche de déploiement est `main`.
3. Examiner puis fusionner la PR qui ajoute cette migration.
4. Vérifier dans Supabase Dashboard > Database > Migrations (ou dans l'historique des migrations) que la migration a été appliquée.
5. Effectuer ensuite les tests d'intégration avec des données fictives.

La simple connexion GitHub ne garantit pas que les migrations sont déployées. Ne pas supposer que la base est prête avant confirmation dans le tableau de bord.

## Sécurité

- Ne jamais committer `.env`, mot de passe PostgreSQL, clé `service_role` ou autre secret.
- La clé serveur reste exclusivement dans les secrets de l'environnement backend.
- Aucun worker n'est démarré par cette migration.
- Aucune action commerciale, publication, dépense ou transaction financière n'est activée.
- Cette migration ne crée pas d'utilisateurs ni de données métier réelles.
