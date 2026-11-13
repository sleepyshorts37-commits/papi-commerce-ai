# Intégration de la reprise à la file persistante

## Contrat livré

`ExecutionQueue.fail` calcule une décision avec `papi_core.retry_policy.decide_retry` puis transmet deux champs explicites au RPC PostgreSQL :
- `p_retry_allowed` : décision de reprise issue de la liste d'erreurs transitoires autorisées ;
- `p_retry_delay_seconds` : délai entier plafonné à 3 600 secondes.

Le calcul utilise un backoff exponentiel de base 15 secondes, un plafond d'une heure et un jitter borné. L'échantillon de jitter est injecté et vaut 0,5 par défaut : les tests restent déterministes. Le RPC de réservation renvoie désormais `attempts` et `max_attempts` depuis la ligne persistée. Le client refuse une réponse qui omet ces champs ou présente un plafond incohérent ; le worker ne substitue plus de valeur par défaut.

## Défense en profondeur SQL

La surcharge `papi_fail_job(..., boolean, integer)` :
- vérifie le format du code d'erreur, les bornes du délai et la cohérence décision/délai ;
- n'autorise la reprise que pour `temporarily_unavailable`, `rate_limited`, `connection_reset` et `service_timeout` ;
- verrouille la ligne et revérifie le worker, le jeton et l'expiration du bail ;
- applique le plafond durable `attempts < max_attempts` avant d'inscrire `retry` ;
- libère le bail dans la même transaction.

L'ancienne surcharge à quatre arguments est conservée dans le schéma mais son droit d'exécution est retiré à `service_role` afin d'empêcher le contournement de la politique. Les anciens clients échouent donc de manière fermée après application de la migration. Le rollback restaure explicitement ce droit. La migration 20261113_002 est enregistrée comme non appliquée et son exécution reste désactivée par politique.

## Limites

- Seules les erreurs de transport Supabase explicitement classées sont transitoires : HTTP 429, 408/504, 425/500/502/503, délais d'attente et réinitialisations de connexion. Les erreurs HTTP d'authentification, validation, conflit ou absence de ressource, les réponses JSON invalides et les erreurs génériques restent permanentes. Aucun texte de message d'exception n'est analysé.
- La migration 20261113_003 ajoute le plafond durable au contrat de claim sans réécrire les jobs. Son rollback restaure l'ancien format de réponse.
- Le jitter par défaut reste déterministe ; un générateur aléatoire de production doit être injecté explicitement par le runtime.
- Cette intégration ne prouve pas l'absence de doublons d'effets externes. Les handlers doivent rester idempotents et contrôler leur bail avant chaque effet.
- Aucun worker permanent, appel Supabase distant ou migration réelle n'est activé.
