# Vérification Supabase 1.4

Commande explicite :

```bash
PYTHONPATH=runtime python -m papi_core supabase-check
```

Le contrôle vérifie trois capacités :
- lecture limitée de `papi_tasks` (colonne id) par GET ;
- lecture limitée de `papi_audit_events` (colonne event_id) par GET ;
- appel de `papi_get_dashboard_snapshot` avec des limites de 1 ligne par ensemble.

Le troisième contrôle utilise HTTP POST pour invoquer une fonction PostgreSQL déclarée `STABLE`, `SECURITY INVOKER` et strictement en lecture seule. Il vérifie la forme de la réponse et le marqueur `single_statement_snapshot`, sans afficher les tâches ni les événements retournés.

Un résultat `ready` confirme uniquement que les deux sondes de table et l'appel de la RPC ont répondu avec une structure attendue. Il ne valide pas l'ensemble du schéma, les sauvegardes, les clés privées, les permissions de chaque agent, ni le démarrage des agents.

Aucun secret n'est affiché et aucune écriture métier n'est effectuée. En cas d'échec, le diagnostic reste générique.
