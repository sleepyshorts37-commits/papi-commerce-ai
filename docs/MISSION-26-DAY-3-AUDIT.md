# Mission 26 — Jour 3 : audit durable et intégrité

## Événements
- `approval.issued`
- `approval.consumed`

Les identifiants d'événement sont déterministes et uniques par approbation. Les détails contiennent uniquement tâche, handler, classe d'action, propriétaire/consommateur et expiration.

## Protection
Le rôle service_role peut lire le registre mais ne reçoit aucun droit direct UPDATE ou DELETE. Les RPC contrôlées, exécutées avec le propriétaire SQL, effectuent les transitions. Les rôles anon et authenticated n'ont aucun accès.

## Atomicité
Si l'insertion d'un événement d'audit échoue, la transaction annule aussi l'émission ou la consommation.
