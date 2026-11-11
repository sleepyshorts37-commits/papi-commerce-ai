# File d'exécution et reprise des travaux

## Capacités ajoutées
- File persistante `papi_jobs`, avec clé d'idempotence unique.
- Réservation atomique par worker avec `FOR UPDATE SKIP LOCKED`.
- Bail temporaire (15 à 900 secondes) et jeton de réservation unique.
- Une réservation expirée peut être reprise par un autre worker.
- Tentatives limitées (maximum 10) et temporisation exponentielle plafonnée à une heure.
- Seul le worker qui détient le bail courant peut terminer ou signaler l'échec.
- Après le nombre maximal de tentatives, le travail passe à `failed`.

## API Python
```python
from papi_core.storage import SupabaseStore
from papi_core.execution_queue import ExecutionQueue

queue = ExecutionQueue(SupabaseStore())
job = queue.claim(worker_id="worker-01", lease_seconds=120)
# Le traitement du handler n'est volontairement pas lancé par cette bibliothèque.
```

Les méthodes `enqueue`, `claim`, `complete` et `fail` pilotent la file. Les handlers métier doivent être ajoutés séparément avec une liste d'autorisation stricte, des permissions par action, des limites et une validation indépendante.

## Sécurité et limites
- Le schéma SQL doit être appliqué manuellement dans un projet Supabase.
- Aucune clé serveur n'est stockée dans GitHub.
- Le code ne lance aucun handler, message, prospection, achat ou paiement.
- Une clé d'idempotence évite les insertions répétées, mais chaque producteur doit réutiliser la même clé pour le même travail logique.
- Un bail expiré permet une reprise ; un handler futur devra aussi être idempotent car un crash après un effet externe mais avant la confirmation peut provoquer une nouvelle tentative.
- Le worker ne doit jamais interpréter un payload comme du code exécutable.
- Aucun worker permanent n'est déployé et aucune exécution autonome n'est activée.
