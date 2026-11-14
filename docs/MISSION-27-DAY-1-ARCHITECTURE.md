# Mission 27 — Jour 1 : architecture et modèle de menace

## Architecture
L'outbox est un registre durable d'intentions métier. Elle est distincte de `papi_jobs` : un job décrit du travail interne confié à un worker ; un événement outbox décrit un fait à propager à un système aval.

## Menaces
- Producteur rejoué après timeout : même clé d'idempotence, un seul événement.
- Clé réutilisée avec une autre charge utile : conflit refusé.
- Deux workers réclament simultanément : verrouillage SKIP LOCKED.
- Worker ancien termine après reprise : lease token de fencing rejeté.
- Crash pendant le traitement : bail expiré récupérable, compteur de tentatives borné.
- Fournisseur accepte puis connexion coupe avant ack : livraison potentiellement ambiguë, à réconcilier via clé aval.

## Limite fondamentale
Une transaction PostgreSQL garantit l'atomicité locale entre mutation métier et insertion outbox uniquement si les deux écritures partagent la même transaction. Elle ne peut pas rendre atomique un appel HTTP externe. L'exactly-once externe n'est pas promis.
