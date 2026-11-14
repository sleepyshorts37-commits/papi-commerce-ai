# Mission 24 — Jour 1 : indicateurs agrégés de santé

## Réalisation
- Ajout de `papi_execution_queue_health()`, fonction PostgreSQL stable et en lecture seule.
- Indicateurs limités aux volumes par statut, baux expirés, travaux prêts et âge du plus ancien travail prêt.
- Aucune donnée de niveau tâche (ID, payload, résultat, jeton ou code d'erreur) dans la réponse.
- Exécution réservée à `service_role`, interdite à `anon`, `authenticated` et `PUBLIC`.
- Test SQL des compteurs, de l'expiration des baux, des permissions et de l'absence de fuite.

## Validation
À confirmer par GitHub Actions sur PostgreSQL jetable.

## Limites
Aucun projet hébergé modifié. Aucun worker, scheduler ou traitement autonome activé. Aucun effet externe, merge ou déploiement.
