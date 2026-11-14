# Mission 23 — Fiabilité des workers et reprise contrôlée

## Objectif
Renforcer la fiabilité du traitement des travaux sans activer d'exécution autonome. La mission couvre les baux, la concurrence, les reprises après échec, l'idempotence des handlers et la validation des événements synchronisés.

## Jour 1/5 — Contrats de bail et perte de réservation
- Tester les bornes des baux et la génération de jetons de réservation distincts.
- Vérifier que le worker ne déclare jamais un job terminé lorsque le bail a été perdu.
- Vérifier le rejet des codes d'erreur susceptibles de contenir des secrets.
- Maintenir les appels réseau et les handlers simulés dans les tests unitaires.

## Jour 2/5 — Réservation exclusive et reprise contrôlée
- Scénarios SQL/PostgreSQL jetables pour réservation, mauvais worker/jeton, retry, expiration et fencing des anciens jetons.
- Validé par les quatre exécutions CI du 14 novembre 2026.

## Jour 3/5 — Concurrence multi-session
- Deux sessions PostgreSQL se chevauchent : la première conserve un verrou de ligne pendant que la seconde réclame un job.
- Vérifier que `FOR UPDATE SKIP LOCKED` attribue deux jobs distincts avec des jetons distincts.
- Finaliser les jobs avec les workers propriétaires ; aucun effet externe.

## Jour 4/5 — Crash/retry et idempotence
- Simuler un worker qui disparaît après réservation ; vérifier la récupération après expiration du bail.
- Vérifier l'unicité de la clé d'idempotence à la création du job, y compris lors d'une nouvelle tentative producteur.
- Vérifier le plafond de tentatives et l'état terminal ; aucun effet métier externe n'est exécuté dans ces tests.

## Jour 5/5 — Validation renforcée des événements, rapport de fiabilité et critères de préproduction.

## Garde-fous
- Aucun worker permanent, aucune boucle autonome et aucun scheduler activé.
- Aucun effet externe, message, prospection, paiement ou transfert financier.
- Aucune connexion à un projet hébergé sans autorisation explicite.
- Aucun secret réel dans Git, les tests ou les journaux.
- Aucune fusion ni aucun déploiement sans approbation explicite.
