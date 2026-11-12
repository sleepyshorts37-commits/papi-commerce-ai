# PAPI TASK ENGINE 0.4 — mémoire de travail et charge dynamique

## Fonction
`papi_core.workload.analyze_workload` produit un instantané déterministe des missions ouvertes : charge par agent, tâches bloquées, échéances dépassées, tâches sans responsable et dépassement de capacité déclarée.

## Données
- Les statuts ouverts sont backlog, ready, in_progress, blocked et review.
- Les tâches done et cancelled sont exclues de la charge.
- Une échéance facultative `due_at` est comparée à l'instant `as_of` fourni explicitement, en ISO 8601 avec fuseau horaire.
- Une capacité n'est utilisée que si elle est fournie explicitement dans `capacity_by_agent`. Sans donnée, l'état reste `unknown`.

## Utilisation

```python
from papi_core.workload import analyze_workload

snapshot = analyze_workload(
    tasks,
    agents=agents,
    as_of="2026-11-12T08:00:00Z",
    capacity_by_agent={"agent-id": 5},
)
```

## Sécurité et limites
- Analyse en lecture seule : aucune modification de tâche ou de registre.
- Les dépassements de capacité déclenchent une recommandation, jamais une réaffectation.
- Une charge de tâches n'est pas une mesure du temps de travail ni une preuve de disponibilité réelle.
- La mémoire de travail s'appuie sur les missions et le journal d'audit existants; aucun historique parallèle n'est créé.
- L'outil ne lance aucun agent, n'envoie aucune notification et n'effectue aucune action externe.
