# Mission 33 — Plan de réalisation sur 20 journées

Programme unique de 20 journées en quatre phases. Le cahier des charges complet est dans [MISSION-33-PROMPT.md](MISSION-33-PROMPT.md).

| Phase | Jours | Livrables | État |
|---|---:|---|---|
| A — Contrats et sécurité | 1–5 | Audit, canonicalisation, visibilité, modèle de menace | Réalisé |
| B — Planification déterministe | 6–10 | Plans référentiels, SHA-256, conflits bloquants, tests | Réalisé |
| C — Approbation et reprise | 11–15 | Signature propriétaire Ed25519, portée exacte, ledger atomique, anti-rejeu | Réalisé |
| D — Validation et transfert | 16–20 | CI PostgreSQL/PostgREST jetable, tests SQL, runbook, revue | Réalisé et validé sur le SHA final ; gates distants explicitement exclus |

## Livrables de code
- `runtime/papi_core/sync_protocol.py` : planification sans écriture, références seulement, digest d'intégrité.
- `runtime/papi_core/sync_approval.py` : approbation signée du propriétaire liée au plan exact.
- `infra/supabase/migrations/017_sync_approval_scope.sql` et rollback prudent.
- Tests unitaires et SQL ; CI applique migration 017 sur ses deux bases PostgreSQL jetables et exécute les contrats.

## Limites
Les environnements CI sont isolés et fictifs. Aucun projet Supabase distant, identifiant de connexion, transfert de données ou approbation de mise en production n'a été fourni. Les tests distants et la restauration sur projet réel restent des prérequis opérationnels, pas des tâches à simuler ni à déclarer réussies.
