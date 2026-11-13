# Récupération des baux et fencing des workers

## Contrat ajouté

`papi_core.lease_recovery.assess_lease_recovery` classe un instantané de job :
- un bail `running` encore valide n'est jamais récupérable ;
- un bail expiré avec des tentatives restantes peut être repris par le mécanisme de claim ;
- un bail expiré au plafond de tentatives doit devenir terminal ;
- les jobs `queued`/`retry` restent éligibles uniquement sous le plafond ;
- les jobs terminaux ne sont jamais éligibles.

L'instantané exige des horodatages avec fuseau et des métadonnées de tentative cohérentes. La sortie ne contient ni jeton de bail ni propriétaire.

## Interaction avec le worker et PostgreSQL

Le RPC de claim demeure l'autorité transactionnelle : verrouillage de ligne, `SKIP LOCKED`, vérification du bail expiré et plafond durable de tentatives. L'évaluateur Python est un contrat de diagnostic/test, pas un remplacement de la décision SQL ni une preuve de propriété.

Le worker existant renouvelle son bail avant de démarrer le handler et fournit `ensure_lease` au contexte du handler. Un handler qui produit des effets externes doit appeler cette garde avant chaque effet et périodiquement pendant les traitements longs. Un bail perdu impose l'arrêt des effets supplémentaires. Les opérations externes doivent également être idempotentes : un bail ne fournit pas une garantie exactly-once.

## Tests et limites

Les tests de ce module sont locaux et déterministes. Les tests PostgreSQL jetables existants couvrent l'application du schéma et le cycle des migrations de claim/retry. Aucun worker continu, ordonnanceur, heartbeat en arrière-plan, accès distant ni migration réelle n'est activé par cette PR.

La durée de bail, le heartbeat périodique pour les handlers longs, la supervision du worker et les procédures d'arrêt gracieux doivent être validés sur une infrastructure isolée avant toute activation.
