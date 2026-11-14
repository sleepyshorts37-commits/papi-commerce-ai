# Préparation de l'environnement Supabase

## Diagnostic local

La commande `python -m papi_core doctor` vérifie uniquement la forme de la configuration locale :
- présence d'une URL HTTPS au format de projet Supabase ;
- présence d'une variable `SUPABASE_SERVICE_ROLE_KEY` ;
- état des interrupteurs de sécurité dans `config/policy.json`.

Le diagnostic n'effectue **aucune connexion réseau**, ne valide pas la clé, n'affiche aucune valeur secrète et n'autorise jamais le démarrage du worker.

## Créer et configurer Supabase

1. Le propriétaire crée lui-même un projet Supabase et vérifie les limites, conditions et éventuels coûts du forfait choisi.
2. Dans le SQL Editor du projet, il exécute le fichier `infra/supabase/schema.sql` après vérification.
3. Il conserve l'URL du projet et une clé serveur dans le gestionnaire de secrets de l'environnement d'exécution.
4. Il définit `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` comme variables d'environnement côté serveur uniquement.
5. Il lance `python -m papi_core doctor` dans l'environnement serveur.
6. Le fichier `runtime/.env.example` est un modèle sans secret ; le copier localement en `.env` est facultatif, mais le vrai fichier doit rester ignoré par Git.
7. Avant toute donnée réelle, il vérifie les permissions, politiques RLS, sauvegardes et procédures de restauration.

Le dépôt ignore `.env`, les fichiers `.env.*` (sauf le modèle `.env.example`) et les fichiers locaux de base de données. Vérifier `git status` avant chaque commit.

Ne jamais utiliser une clé `service_role` dans une application mobile/navigateur, une issue GitHub, un dépôt, un journal ou une conversation. Ne jamais commiter un fichier `.env`. Si une clé est exposée, la révoquer/renouveler immédiatement depuis Supabase.

## Adaptateur PAPI AI WORKERS\n\nLe runtime expose `papi_core.worker_store.SupabaseWorkerStore`, à construire explicitement autour d'une instance `papi_core.storage.SupabaseStore`. L'adaptateur fournit `sync_event(event, expected_version=...)` pour l'écriture transactionnelle idempotente et `load_worker_inputs()` pour lire les trois domaines. `build_command_center(..., worker_store=adapter)` active explicitement la lecture centrale ; sans cet argument, le tableau de bord reste local et n'effectue aucun appel réseau. Le module ne crée jamais de client automatiquement et ne relance pas automatiquement les écritures après une erreur réseau.\n\nLa variable recommandée est `SUPABASE_SERVICE_ROLE_KEY` côté serveur uniquement. `SUPABASE_KEY` reste accepté pour compatibilité historique, mais doit également être une clé secrète serveur. La clé `service_role` contourne RLS : limiter strictement son accès au backend, protéger l'environnement et ne jamais la transmettre à un agent/frontend.\n\n## État actuel et limites

- Aucun projet Supabase n'est créé ni connecté par ce dépôt.
- Le SQL n'a pas été exécuté sur un projet distant.
- Les tests utilisent des simulations et ne valident pas un service distant.
- `execution_enabled` reste désactivé par défaut ; les actions externes, financières et juridiques restent bloquées.
- Le diagnostic ne constitue pas un test de disponibilité ni un audit des droits.
- Le worker ne doit pas être lancé avant revue de sécurité, configuration serveur et tests d'intégration autorisés.


## Adaptateur d'identité partagé
Le runtime expose `papi_core.shared_identity.SupabaseIdentityVerifier`, à injecter explicitement dans le worker côté serveur. Il nécessite les tables et la RPC du schéma SQL, ainsi qu'un `SUPABASE_SERVICE_ROLE_KEY` conservé dans les secrets serveur. Ne jamais exposer une clé `service_role` dans un client ou un dépôt. Avant utilisation, appliquer le SQL, vérifier les droits du rôle serveur, puis effectuer les tests d'intégration avec des identités de test.
