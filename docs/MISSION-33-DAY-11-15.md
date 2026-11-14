# Mission 33 — Jours 11 à 15 : approbation et reprise gouvernées

11. Définition d'une approbation liée au digest du plan, à la destination et à la liste exacte des actions.
12. Signature Ed25519 obligatoire par l'identité propriétaire désignée ; l'agent auteur du plan ne peut pas s'approuver lui-même.
13. Identifiants d'action immuables et vérification de nonce anti-rejeu ; consommation SQL atomique et auditée.
14. Contrat d'état défini : proposed, approved, applying, completed, partial, blocked, expired. L'exécution reste désactivée dans cette mission.
15. Runbook de reprise : timeout réseau, crash, rejeu, lease expiré, conflit et arbitrage humain.

## Livrables exécutés
- `runtime/papi_core/sync_approval.py` vérifie l'enveloppe Ed25519, l'identité propriétaire, la tâche, l'expiration et l'égalité stricte du digest, de la destination et des action IDs.
- Migration `017_sync_approval_scope.sql` étend le ledger existant avec la portée exacte du plan.
- RPC `papi_issue_sync_approval` et `papi_consume_sync_approval` : fonctions réservées à `service_role`, consommation atomique à usage unique et audit transactionnel.
- Tests unitaires signés, tests SQL de périmètre et de rejeu.
- La validation cryptographique consomme un nonce anti-rejeu ; la consommation durable de l'approbation doit ensuite être appelée côté backend via la RPC. Aucune action de synchronisation n'est exécutée.
