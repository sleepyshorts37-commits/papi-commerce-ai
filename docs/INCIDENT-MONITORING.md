# Surveillance technique et gestion des incidents

## Composant de base

`runtime/papi_core/monitoring.py` fournit une fonction pure qui évalue des signaux de santé fournis par l'appelant. Elle calcule l'état global, détecte les signaux périmés ou datés dans le futur et génère une liste d'incidents synthétiques.

États : `healthy`, `degraded`, `unavailable`, `unknown`. La gravité globale retient le plus sévère. Par défaut, un signal de plus de 300 secondes est classé `unknown`.

## Exemple local

```python
from datetime import datetime, timezone
from papi_core.monitoring import evaluate_health_snapshot

report = evaluate_health_snapshot(
    [{"id": "queue", "status": "degraded",
      "observed_at": datetime.now(timezone.utc).isoformat()}]
)
print(report)
```

## Garde-fous

- Le module n'effectue aucune sonde réseau, ne contacte aucune API et ne lit aucun secret.
- Aucun redémarrage, retry, arrêt de worker ou changement de configuration automatique.
- Les détails libres des sondes ne sont jamais copiés dans le rapport ; ne pas transmettre de secrets dans les identifiants.
- Un signal absent doit être déclaré par l'appelant comme `unknown`, pas interprété comme sain.
- Les incidents calculés sont des observations, pas la preuve qu'un incident a été acquitté ou résolu.

## Ce qui reste à construire

Collecteurs réels, stockage durable des événements, déduplication/corrélation, alerting, acquittement, escalade, tableaux de bord et surveillance des quotas/crédits. Toute intégration externe nécessitera authentification, politique d'accès et tests séparés.
