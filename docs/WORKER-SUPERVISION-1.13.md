# PAPI WORKER SUPERVISION 1.13

## Objectif
Ajouter un diagnostic déterministe de santé des workers et des jobs à partir d'un instantané explicitement fourni.

## Détections
- worker déclaré hors ligne ou suspendu ;
- heartbeat absent (état non vérifié) ou trop ancien ;
- identité inactive/incomplète ou permissions divergentes ;
- bail d'un job en cours expiré ;
- échecs répétés et tentatives épuisées.

## Contrat
`build_worker_supervision(jobs, workers, as_of=..., heartbeat_timeout_seconds=180, repeated_failure_threshold=3)`.
Les dates doivent être ISO-8601 avec fuseau horaire. Les seuils sont des entiers strictement positifs. Les identifiants doivent être uniques. Les entrées invalides provoquent une erreur (fail-closed).

## Sécurité
Lecture seule. Aucun retry, claim, réaffectation, extension de bail, suspension, notification ou démarrage de worker. Les recommandations sont informatives et toute reprise nécessite une validation humaine. Aucun secret ni payload n'est exposé.

## Limites
Le diagnostic ne prouve pas l'état réel d'un worker : il reflète uniquement l'instantané reçu. Un heartbeat absent est « non vérifié », pas une preuve de panne. Le module n'est pas connecté à Supabase et aucun worker n'est déployé.
