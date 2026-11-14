# Mission 27 — Jour 4 : idempotence aval et résilience

## Contrat aval
Le consommateur transmet la même clé d'idempotence à chaque tentative si le fournisseur prend en charge cette fonctionnalité. Pour les consommateurs internes, utiliser une inbox avec contrainte unique sur l'événement source.

## Panne ambiguë
Si le fournisseur accepte une requête mais que le worker perd la réponse avant l'ack, l'événement peut être repris. Sans idempotence fournisseur ni API de rapprochement, un doublon externe reste possible. Le worker doit alors passer en réconciliation manuelle, jamais inventer une réussite.

## Tests
Couverture des clés dupliquées, intentions contradictoires, leases erronés, fencing, retry, dead-letter, historique des tentatives et claim concurrent.
