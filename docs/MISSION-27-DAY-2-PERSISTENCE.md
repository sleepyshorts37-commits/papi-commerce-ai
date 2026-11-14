# Mission 27 — Jour 2 : persistance et idempotence producteur

## Implémentation
Ajout de `papi_outbox`, `papi_outbox_attempts` et `papi_enqueue_outbox`.

## Contrat de déduplication
- Même clé et même event_type, aggregate_id, payload et max_attempts : retourne le même UUID.
- Même clé avec intention différente : erreur unique_violation.
- Payload JSON objet limité à 16 KiB.
- Clé d'idempotence unique indexée.

## Contrat transactionnel
Le service producteur doit exécuter sa mutation métier et `papi_enqueue_outbox` sur la même connexion/transaction PostgreSQL. Un appel REST séparé après commit n'est pas atomique et ne respecte pas ce contrat. L'intégration métier spécifique est différée tant que les domaines et transactions concernés ne sont pas identifiés.
