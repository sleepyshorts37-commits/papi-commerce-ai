# PAPI TASK LEASE & HEARTBEAT 1.6

## Fonctionnalités

Le module `papi_core.task_lease` ajoute trois primitives pures :
- `claim_task` : réserve une tâche `ready` pour son agent propriétaire actif, sous réserve des approbations.
- `heartbeat_task` : renouvelle un bail existant uniquement pour le même worker et avant son expiration.
- `expire_task_lease` : remet une tâche `in_progress` en `ready` lorsque le bail a expiré, puis retire le bail périmé.

Durée autorisée : 30 à 3 600 secondes. Chaque transition retourne un événement d'audit.

## Limites importantes

- Aucune boucle de worker, planification périodique, notification ou exécution de handler n'est créée.
- Ces fonctions travaillent sur des copies en mémoire. Elles ne fournissent PAS d'exclusion mutuelle entre plusieurs processus.
- Avant tout déploiement multi-worker, la réservation, le heartbeat et l'expiration doivent être implémentés dans des transactions PostgreSQL atomiques (verrouillage de ligne ou mise à jour conditionnelle par version), avec unicité du bail et contrôle de concurrence.
- Un worker ne doit jamais traiter une tâche uniquement parce qu'il a reçu une copie locale : il devra confirmer le bail courant en stockage au moment de chaque opération.
- L'authentification Ed25519 et le précontrôle d'exécution de la version 1.5 restent des étapes séparées et obligatoires.
- Le précontrôle 1.5 reste `preflight_only`; aucune action métier n'est déclenchée.

## Sécurité et déploiement

La politique demeure `execution_enabled: false`, budget 0 FCFA et actions externes désactivées. Les 40 profils restent planifiés/incomplets. Ce module n'active aucun agent et ne contacte pas Supabase.
