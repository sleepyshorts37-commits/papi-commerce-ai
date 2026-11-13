# Intégration de la reprise à la file persistante

## Contrat livré

`ExecutionQueue.fail` calcule une décision avec `papi_core.retry_policy.decide_retry` puis transmet deux champs explicites au RPC PostgreSQL :
- `p_retry_allowed` : décision de reprise issue de la liste d'erreurs transitoires autorisées ;
- `p_retry_delay_seconds` : délai entier plafonné à 3 600 secondes.

Le calcul utilise un backoff exponentiel de base 15 secondes, un plafond d'une heure et un jitter borné. L'échantillon de jitter est injecté et vaut 0,5 par défaut : les tests restent déterministes. Le worker transmet le numéro de tentative retourné par la réservation ; si le plafond n'est pas présent dans la réponse, le client conserve le plafond de création actuel (5).

## Défense en profondeur SQL

La surcharge `papi_fail_job(..., boolean, integer)` :
- vérifie le format du code d'erreur, les bornes du délai et la cohérence décision/délai ;
- n'autorise la reprise que pour `temporarily_unavailable`, `rate_limited`, `connection_reset` et `service_timeout` ;
- verrouille la ligne et revérifie le worker, le jeton et l'expiration du bail ;
- applique le plafond durable `attempts < max_attempts` avant d'inscrire `retry` ;
- libère le bail dans la même transaction.

L'ancienne surcharge à quatre arguments est conservée pour compatibilité avec les anciens clients. Le nouveau client utilise exclusivement la surcharge à six arguments. La migration 20261113_002 est enregistrée comme non appliquée et son exécution reste désactivée par politique.

## Limites

- Les erreurs génériques du worker restent permanentes par défaut ; aucune exception réseau n'est reclassée automatiquement comme transitoire.
- La réponse de claim ne transporte pas encore la valeur durable `max_attempts` ; le client utilise actuellement 5, valeur fixée par `enqueue`. L'harmonisation des anciens jobs et de ce plafond reste à faire.
- Le jitter par défaut est déterministe, pas une source d'aléa de production.
- Cette intégration ne prouve pas l'absence de doublons d'effets externes. Les handlers doivent rester idempotents et contrôler leur bail avant chaque effet.
- Aucun worker permanent, appel Supabase distant ou migration réelle n'est activé.
