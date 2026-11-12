# PAPI COMMAND CENTER distant 0.9

## Fonctionnement
\`papi_core.remote_command_center.build_remote_command_center(store, ...)\` construit un tableau de bord à partir :
- du registre des agents local \`data/agents.json\` ;
- d'un instantané paginé des tâches Supabase ;
- d'une lecture paginée du journal d'audit Supabase.

Les tâches sont triées par identifiant et validées (objet, cohérence de l'identifiant, version positive). Les événements sont triés par date et identifiant et validés avec le schéma central. Les historiques de tous les agents sont calculés après une seule lecture du journal, évitant une requête complète par agent.

## Cohérence
Les lectures des tâches et des événements sont indépendantes et ne sont pas encapsulées dans une transaction de lecture unique. Le résultat indique donc \`snapshot_consistency=independent_reads_not_transactional\`. Une version future pourra ajouter une RPC de snapshot transactionnel.

## Limites et sécurité
- Lecture seule : uniquement des requêtes GET via les nouvelles méthodes utilisées.
- Limites par défaut : 500 lignes par page, maximum 20 pages.
- Si la limite est atteinte sans page partielle, le système échoue plutôt que de retourner un instantané tronqué.
- Les agents restent lus depuis le registre local et ne sont pas activés.
- Aucun worker, message, achat, paiement ou action externe n'est déclenché.
- Les tests simulent Supabase ; ils ne valident pas une connexion réelle ni les permissions du projet.

## Exécution
Le module est une fonction Python appelable depuis un environnement serveur configuré. Il ne remplace pas encore la commande locale dashboard et ne constitue pas une interface web hébergée.
