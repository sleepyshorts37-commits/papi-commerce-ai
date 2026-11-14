# Mission 26 — Jour 2 : émission et consommation atomiques

## RPC créées
- `papi_issue_approval` : enregistre une approbation à portée fixe et de durée maximale de 15 minutes.
- `papi_consume_approval` : consomme l'approbation par un UPDATE conditionnel unique.

## Garantie transactionnelle
La mise à jour de la ligne est sérialisée par PostgreSQL. Le prédicat `consumed_at is null` signifie qu'un seul appel peut faire passer l'approbation de disponible à consommée. L'événement d'audit est inséré dans la même transaction.

## Limites
La fonction de consommation ne lance aucun handler et ne garantit pas qu'une opération externe a été réalisée. Les effets métier futurs devront posséder leur propre clé d'idempotence.
