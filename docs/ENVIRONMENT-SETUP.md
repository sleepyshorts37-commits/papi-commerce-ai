# Préparation de l'environnement Supabase

## Diagnostic local

La commande `python -m papi_core doctor` vérifie uniquement la forme de la configuration locale :
- présence d'une URL HTTPS au format de projet Supabase ;
- présence d'une variable `SUPABASE_KEY` ;
- état des interrupteurs de sécurité dans `config/policy.json`.

Le diagnostic n'effectue **aucune connexion réseau**, ne valide pas la clé, n'affiche aucune valeur secrète et n'autorise jamais le démarrage du worker.

## Créer et configurer Supabase

1. Le propriétaire crée lui-même un projet Supabase et vérifie les limites, conditions et éventuels coûts du forfait choisi.
2. Dans le SQL Editor du projet, il exécute le fichier `infra/supabase/schema.sql` après vérification.
3. Il conserve l'URL du projet et une clé serveur dans le gestionnaire de secrets de l'environnement d'exécution.
4. Il définit `SUPABASE_URL` et `SUPABASE_KEY` comme variables d'environnement côté serveur uniquement.
5. Il lance `python -m papi_core doctor` dans l'environnement serveur.
6. Le fichier `runtime/.env.example` est un modèle sans secret ; le copier localement en `.env` est facultatif, mais le vrai fichier doit rester ignoré par Git.\n7. Avant toute donnée réelle, il vérifie les permissions, politiques RLS, sauvegardes et procédures de restauration.

Le dépôt ignore `.env`, les fichiers `.env.*` (sauf le modèle `.env.example`) et les fichiers locaux de base de données. Vérifier `git status` avant chaque commit.\n\nNe jamais utiliser une clé `service_role` dans une application mobile/navigateur, une issue GitHub, un dépôt, un journal ou une conversation. Ne jamais commiter un fichier `.env`. Si une clé est exposée, la révoquer/renouveler immédiatement depuis Supabase.

## État actuel et limites

- Aucun projet Supabase n'est créé ni connecté par ce dépôt.
- Le SQL n'a pas été exécuté sur un projet distant.
- Les tests utilisent des simulations et ne valident pas un service distant.
- `execution_enabled` reste désactivé par défaut ; les actions externes, financières et juridiques restent bloquées.
- Le diagnostic ne constitue pas un test de disponibilité ni un audit des droits.
- Le worker ne doit pas être lancé avant revue de sécurité, configuration serveur et tests d'intégration autorisés.


## Adaptateur d'identité partagé
Le runtime expose `papi_core.shared_identity.SupabaseIdentityVerifier`, à injecter explicitement dans le worker côté serveur. Il nécessite les tables et la RPC du schéma SQL, ainsi qu'un `SUPABASE_KEY` conservé dans les secrets serveur. Ne jamais exposer une clé `service_role` dans un client ou un dépôt. Avant utilisation, appliquer le SQL, vérifier les droits du rôle serveur, puis effectuer les tests d'intégration avec des identités de test.
