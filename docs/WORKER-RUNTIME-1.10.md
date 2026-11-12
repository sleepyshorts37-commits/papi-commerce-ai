# PAPI WORKER RUNTIME ENGINE 1.10

## Moteur de dispatch contrôlé
`runtime/papi_core/worker_runtime.py` fournit un point d'entrée unique pour traiter un job local :
1. vérification de cohérence entre job, tâche et handler ;
2. authentification worker obligatoire via un callback qui doit appeler la vérification Ed25519 complète de la phase 1.9 ;
3. contrôle de l'identité et du job visé ;
4. prévalidation fail-closed via `evaluate_execution_readiness` ;
5. vérification du handler dans la liste de politique et le registre local ;
6. appel du handler et validation du résultat JSON.

Deux handlers locaux sont fournis : `internal.echo` et `report.preview`. Aucun accès réseau, publication, paiement, transfert ou achat n'est implémenté.

## Sécurité et état
La politique versionnée du dépôt conserve `execution_enabled: false`, budget 0 FCFA et actions externes désactivées. Dans cette configuration, le moteur renvoie `held` et n'appelle aucun handler. Les tests activent une politique factice uniquement en mémoire pour vérifier le dispatch local ; cela ne modifie pas la configuration du produit.

Ce module ne lance pas de processus permanent, ne réserve pas lui-même les jobs Supabase et ne confirme pas le job dans la file. Le worker de production devra authentifier chaque appel, utiliser les RPC atomiques de lease et clôturer le job après résultat. Ne pas exposer directement le moteur à des entrées non fiables.
