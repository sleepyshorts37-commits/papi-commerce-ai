# Machine à états des missions PAPI

## Cycle de vie contrôlé
`backlog → ready → in_progress → review → done`

Branches autorisées :
- `backlog → ready | cancelled`
- `ready → in_progress | blocked | cancelled`
- `in_progress → blocked | review | cancelled`
- `blocked → ready | cancelled`
- `review → in_progress | blocked | done`
- `done` et `cancelled` sont terminaux.

## Règles
- Une tâche avec `approval_required=true` ne peut passer en exécution sans décision `approved`.
- Une décision d'approbation finale ne peut pas être écrasée. Une nouvelle demande doit être créée si le contexte change.
- Une tâche ne peut être clôturée qu'après passage en `review` et ajout d'une preuve ou d'un lien de résultat.
- Chaque transition retourne un événement d'audit horodaté.
- Le module est pur : il ne modifie aucun fichier et n'exécute aucune action externe.

## Exemple Python
```python
from papi_core.state_machine import transition_task, approve_task

task, approval_event = approve_task(
    task, approver="owner", decision="approved", reason="Budget validé"
)
task, event = transition_task(task, "in_progress", actor="marietou")
```

## Limites
La machine à états est implémentée et testée par code, mais n'est pas encore connectée à un stockage partagé ou aux GitHub Issues. L'écriture coordonnée de l'état et de son journal nécessitera une transaction dans une base de données pour éviter les incohérences en cas de panne.
