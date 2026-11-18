# Revue de sécurité — addendum du 18 novembre 2026

## Portée

Cet addendum complète la revue ciblée du 14 novembre pour la branche d'audit worker par tentative. Il décrit le code et les tests du dépôt ; il ne constitue ni un audit indépendant certifié, ni un test d'intrusion, ni une validation de production.

## Attribution après authentification

La vérification de signature, la liaison à l'agent, à la permission, à la tâche et au handler, ainsi que l'anti-rejeu constituent la frontière d'authentification. Dès qu'elles réussissent, le code émet un principal scellé avant de charger et d'appliquer la politique métier.

Toute erreur de politique attendue après cette frontière est convertie en `AuthenticatedAuthorizationDenied`, qui transporte uniquement le principal vérifié. Le worker intercepte ce type avant `AccessDenied` et produit un événement `job.blocked` attribué à cet agent avec `permission_denied`. Les échecs de signature ou de liaison restent attribués au worker système. Aucun handler ne démarre dans les deux cas.

## Audit par tentative

Les événements worker incluent les identifiants du job, de la tâche, de la tentative UUID, du worker et de l'agent authentifié lorsqu'il existe. Le `dedupe_id` est dérivé de `job_id + attempt_id + action` : les tentatives distinctes conservent des identifiants d'événement distincts, tandis qu'un rejeu du même événement dans la même tentative est dédupliqué.

L'événement `job.handler_started` reste une barrière fail-closed. Les événements terminaux sont best-effort après une transition de file déjà confirmée. Le journal local chaîné est tamper-evident, mais ne résiste pas à un attaquant capable de réécrire le journal et ses checkpoints locaux.

## Validation et limites

- Les régressions couvrent le refus avant authentification, le refus de politique après authentification, l'attribution de l'acteur et l'absence d'appel au handler.
- Les tests de déduplication par tentative et d'écriture concurrente restent présents dans `tests/test_worker_attempt_audit.py`.
- Les vérifications GitHub Actions doivent être lues sur le SHA exact de la branche de correction ; les résultats d'un SHA antérieur ne valident pas les commits suivants.
- Aucun service d'ancrage externe indépendant n'est configuré ici.
- Aucun worker/agent réel, déploiement, base de production, opération financière ou communication externe n'est utilisé.
- Aucun effet externe ne bénéficie d'une garantie exactly-once par le seul fait de disposer d'un `attempt_id`.

## Décision

Conserver la PR en brouillon jusqu'à l'exécution réussie des workflows sur son SHA courant, à une revue indépendante et à la validation des scénarios de reprise et d'idempotence sur infrastructure jetable. Ne pas fusionner ni déployer sur la base de cette revue.
