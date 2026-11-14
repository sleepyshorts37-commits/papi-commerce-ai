# Mission 28 — Jour 4 : exécution et supervision

`papi_claim_worker_job` ne réclame que les jobs affectés au worker concerné. Il utilise un verrou SKIP LOCKED, un bail et un jeton de fencing. `papi_finish_worker_job` vérifie worker, jeton et bail avant de terminer, échouer ou remettre en retry. Les changements de job et d'affectation sont transactionnels.
