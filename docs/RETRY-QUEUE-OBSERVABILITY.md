# Observabilité de la file retry/queue

## Contrat livré

`papi_core.queue_observability.evaluate_queue_snapshot` transforme un snapshot explicite de jobs en compteurs et alertes synthétiques. Les statuts acceptés reflètent le schéma SQL actuel : `queued`, `running`, `retry`, `done`, `failed`.

Le rapport calcule uniquement à partir des champs fournis :
- volumes par statut et backlog actif ;
- âge du plus ancien job en attente/reprise ;
- reprises dont `available_at` est arrivé et délai de la prochaine reprise ;
- baux `running` expirés ;
- jobs encore actifs ayant atteint leur plafond de tentatives.

Les baux expirés et les jobs actifs au plafond dégradent l'état global. Les jobs terminaux `failed` au plafond ne sont pas comptés comme jobs actifs bloqués.

## Sécurité et limites

- Le module est pur : aucune lecture Supabase, sonde réseau, émission de métrique, notification ou action corrective.
- Le collecteur devra fournir un snapshot cohérent, horodaté et paginé. Cette fonction ne prouve ni exhaustivité ni fraîcheur de la collecte.
- Payloads, identifiants, tokens de bail, messages d'erreur et données métier ne sont jamais recopiés dans le résultat.
- Les valeurs sont des agrégats calculés, pas des compteurs persistés ni une preuve de débit historique. Le taux de retry nécessite une fenêtre temporelle et des événements durables ; il n'est pas inventé ici.
- Les seuils d'alerte opérationnels, l'export Prometheus/OpenTelemetry et le routage des notifications restent à intégrer et à valider.

## Activation

L'intégration à un collecteur ou dashboard doit être une étape séparée, avec contrôle d'accès, pagination, limites de rétention, tests de charge et revue des données exposées. Aucun worker permanent ni alerting externe n'est activé par cette PR.
