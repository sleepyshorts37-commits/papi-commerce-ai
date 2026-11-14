# Mission 23 — Jour 2 : contrats PostgreSQL de la file

## Réalisé
- Ajout de `tests/sql/test_execution_queue.sql`, exécuté contre PostgreSQL jetable dans la CI.
- Deux workers de test réclament deux jobs distincts.
- Refus de finalisation avec un propriétaire incorrect ou un jeton erroné.
- Finalisation acceptée uniquement avec le propriétaire et le jeton courants.
- Vérification de la transition `running → retry`, de l'incrément du compteur de tentatives et de la reprise du job.
- Simulation d'un bail expiré en base, nouvelle réservation avec un jeton différent, rejet de l'ancien propriétaire, puis finalisation par le nouveau propriétaire.
- Ajout du test SQL à `.github/workflows/papi-core-tests.yml`.

## Portée et limites
Les fonctions PL/pgSQL réelles sont exercées sur PostgreSQL jetable. Les deux réservations successives confirment l'absence de double attribution dans ce scénario, mais ne remplacent pas encore un test multi-session concurrent avec transactions qui se chevauchent ; celui-ci reste prévu au Jour 3.

## Gouvernance
Aucun service hébergé n'est utilisé. Aucun handler métier, effet externe, paiement ou worker permanent n'est lancé. Exécution uniquement dans la base éphémère de CI.
