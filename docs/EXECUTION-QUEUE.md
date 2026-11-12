# File d'exécution et reprise des travaux

## Capacités ajoutées
- File persistante `papi_jobs`, avec clé d'idempotence unique.
- Réservation atomique par worker avec `FOR UPDATE SKIP LOCKED`.
- Bail temporaire (15 à 900 secondes) et jeton de réservation unique.
- Une réservation expirée peut être reprise par un autre worker.
- Tentatives limitées (maximum 10) et temporisation exponentielle plafonnée à une heure.
- Seul le worker qui détient le bail courant peut terminer ou signaler l'échec.
- Renouvellement atomique et clôturé par worker + jeton : un bail expiré ou remplacé ne peut pas être ressuscité.
- Le worker renouvelle le bail avant de démarrer le handler et refuse le démarrage si le renouvellement échoue.
- Le contexte du handler expose `ensure_lease()` : le handler doit l'appeler périodiquement pendant les traitements longs et immédiatement avant chaque effet externe. Un échec lève `LeaseLostError`, arrête le flux coopératif et empêche la confirmation du job.
- Après le nombre maximal de tentatives, le travail passe à `failed`.

## API Python
```python
from papi_core.storage import SupabaseStore
from papi_core.execution_queue import ExecutionQueue

queue = ExecutionQueue(SupabaseStore())
job = queue.claim(worker_id="worker-01", lease_seconds=120)
# Le traitement du handler n'est volontairement pas lancé par cette bibliothèque.
```

Les méthodes `enqueue`, `claim`, `renew`, `complete` et `fail` pilotent la file. `renew` prolonge un bail encore valide jusqu'à 900 secondes ; elle ne peut pas récupérer un bail déjà expiré. Les handlers métier doivent être ajoutés séparément avec une liste d'autorisation stricte, des permissions par action, des limites et une validation indépendante.

## Sécurité et limites
- Le schéma SQL doit être appliqué manuellement dans un projet Supabase.
- Aucune clé serveur n'est stockée dans GitHub.
- Le code ne lance aucun handler, message, prospection, achat ou paiement.
- Une clé d'idempotence évite les insertions répétées, mais chaque producteur doit réutiliser la même clé pour le même travail logique.
- Un bail expiré permet une reprise ; un handler devra aussi être idempotent car un crash après un effet externe mais avant la confirmation peut provoquer une nouvelle tentative.
- `ensure_lease()` est un garde coopératif, pas un heartbeat en arrière-plan : il ne protège que les handlers qui l'appellent. Un handler bloqué ou non coopératif peut continuer jusqu'à son prochain point de contrôle. Les systèmes externes doivent accepter une clé d'idempotence/fencing ; un effet externe déjà engagé peut sinon se poursuivre après une reprise par un autre worker.
- Le worker ne doit jamais interpréter un payload comme du code exécutable.
- Aucun worker permanent n'est déployé et aucune exécution autonome n'est activée.
