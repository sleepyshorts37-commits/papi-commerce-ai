# Mission 24 — Clôture consolidée (10 jours)

## Statut
Livrables des jours 6 à 10 ajoutés sur une branche de continuation. La clôture technique dépend du succès des workflows push et pull_request sur le SHA final exact.

## Progression
- Jours 1 à 5 : validés antérieurement.
- Jour 6 : protocole performance PostgreSQL + probe SQL read-only intégrée à CI.
- Jour 7 : classification SEV, arbre de décision et modèle d'alerte manuelle.
- Jour 8 : procédure backup/restore sur bases jetables, contrôles post-restauration.
- Jour 9 : inventaire des tests de concurrence/baux/idempotence et procédure de panne ; coupure/redémarrage non exécutés.
- Jour 10 : audit des risques et limites opérationnelles.
- Aucun index supplémentaire n'a été ajouté sans preuve mesurée.

## Validation CI attendue
Les deux jobs du workflow PAPI core tests doivent réussir sur le SHA final :
1. Tests PostgreSQL 16 jetable, incluant les probes de performance read-only.
2. Intégration PostgREST locale, incluant migrations 006 à 009, diagnostic et probes de performance.

## Limites connues
- Les mesures CI ne sont pas des benchmarks de production.
- L'exercice de coupure/redémarrage PostgreSQL est documenté, non exécuté.
- Les procédures de sauvegarde/restauration sont destinées à des bases jetables ; aucun backup de production n'a été réalisé.
- Les tests locaux ne valident pas Supabase hébergé, Auth, API Gateway, Storage ou Realtime.
- Les notifications, schedulers, workers permanents, reprises automatiques et purges réelles restent désactivés.

## Gouvernance
Aucune fusion, aucun déploiement, aucune action externe ou financière n'a été effectué. Toute opération destructive ou de production exige une autorisation explicite.
