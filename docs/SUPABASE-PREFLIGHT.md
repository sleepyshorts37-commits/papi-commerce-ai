# Préflight Supabase hors ligne

## Objectif
Fournir un contrôle reproductible avant qu'un opérateur ne configure ou n'applique les migrations à un projet Supabase. Cette commande est strictement locale : elle ne crée aucun client HTTP, ne contacte aucun hôte et n'applique aucune migration.

## Commandes

```bash
PYTHONPATH=runtime python -m papi_core supabase-preflight
PYTHONPATH=runtime python -m papi_core supabase-preflight --require-configured
```

Le rapport indique l'inventaire ordonné des migrations, leur SHA-256, la présence d'un rollback, la cohérence de la séquence, l'état de configuration et les fichiers .env détectés. Il ne révèle jamais la valeur d'une clé.

## Conditions vérifiées
- Schéma SQL principal présent et non vide.
- Fichiers de migration ascendante nommés `NNN_description.sql`.
- Numéros de migration uniques et sans trou dans la séquence livrée.
- Empreinte SHA-256 et taille de chaque migration.
- Disponibilité d'un fichier `_down.sql` indiquée sans prétendre qu'un rollback est sûr.
- URL HTTPS de projet au domaine `*.supabase.co`, sans identifiants, port, chemin, query ni fragment.
- Présence de `SUPABASE_SERVICE_ROLE_KEY` ou de l'ancien `SUPABASE_KEY`.
- Détection de fichiers locaux `.env*`, sauf modèles explicitement autorisés.

## Limites et sécurité
- La présence d'une clé n'en prouve ni la validité ni les droits.
- La commande ne teste pas la connectivité, le projet, les migrations déjà appliquées, RLS effectif ou la disponibilité du service.
- Un SHA local n'est pas une preuve de l'état de la base distante.
- Aucun SQL n'est envoyé à Supabase.
- `remote_changes_permitted`, `remote_migrations_applied` et `deployment_performed` restent toujours faux.
- La clé `service_role` reste exclusivement côté serveur et ne doit jamais être placée dans Git, un navigateur, une application mobile ou un agent.
- Avant un test hébergé, le propriétaire doit désigner un projet de test, fournir les accès via un gestionnaire de secrets et autoriser explicitement les opérations envisagées.
- La revue de sécurité indépendante et les tests réels restent obligatoires avant production.

## Résultat attendu
Un rapport `ready_for_operator_review` signifie uniquement que les fichiers et variables locales satisfont les contrôles statiques. Il ne signifie pas « Supabase opérationnel » ni « prêt pour production ».
