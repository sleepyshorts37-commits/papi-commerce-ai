# Mission 27 — Jour 3 : claim, bail, fencing et retry

## Fonctions
- `papi_claim_outbox` réclame un événement prêt avec `FOR UPDATE SKIP LOCKED`.
- Le bail est borné entre 15 et 900 secondes.
- Chaque claim augmente attempts et génère un lease_token côté worker.
- Un bail expiré peut être repris avec un nouveau jeton.
- `papi_finish_outbox` valide worker + jeton + bail actif.

## Retry
Backoff exponentiel 15, 30, 60, 120... plafonné à 3600 secondes. À max_attempts, l'événement passe en dead_letter. Les événements de claim, retry, livraison et dead-letter sont inscrits dans le journal append-only.
