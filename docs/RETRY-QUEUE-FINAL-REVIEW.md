# Revue finale — intégration queue / retry / leases

## Périmètre vérifié

Cette revue relie les contrats locaux de reprise, récupération de bail et observabilité :
- `decide_retry` distingue les erreurs transitoires des erreurs permanentes et borne le backoff ;
- `assess_lease_recovery` refuse de voler un bail encore valide, autorise l'évaluation d'un bail expiré sous le plafond et bloque les jobs terminaux ;
- `evaluate_queue_snapshot` agrège les états fournis sans accès réseau/DB ni exposition des payloads et identifiants.

## Correction de cohérence

Le paramètre `stale_running_seconds` de l'observabilité est maintenant appliqué comme délai de grâce après `lease_until`. Un bail tout juste expiré ne déclenche donc pas immédiatement l'alerte ; le seuil est vérifié explicitement par un test de frontière. Cette alerte est un signal d'observabilité, pas une autorisation de claim.

## Validation

Le test de contrat final couvre une reprise transitoire, la décision de récupération, la présence du job dans le snapshot et l'absence de fuite de données privées. Il vérifie également qu'une erreur permanente n'est pas replanifiée et que le délai de grâce d'observabilité est respecté.

La CI du dépôt continue de vérifier le registre, la suite unitaire complète et les migrations sur PostgreSQL jetable. Aucune migration distante n'est exécutée.

## Limites et décision opérationnelle

- Le RPC PostgreSQL reste l'autorité transactionnelle pour claim, renouvellement et transitions.
- Les handlers doivent vérifier leur bail avant les effets externes et rester idempotents.
- Aucun mécanisme exactly-once n'est garanti.
- Aucun worker permanent, scheduler, heartbeat de production, accès distant, dépense ou déploiement n'est activé par cette phase.
- La phase est techniquement prête pour une revue humaine des PR empilées ; elle n'est pas une autorisation de mise en production.
