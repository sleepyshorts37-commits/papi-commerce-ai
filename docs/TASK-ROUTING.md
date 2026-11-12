# PAPI TASK ROUTING 0.3 — recommandations intelligentes

## Objectif
Classer les agents susceptibles de recevoir une tâche à partir des informations disponibles, sans effectuer l'affectation. Le module `papi_core.task_routing` est déterministe, local et sans appel externe.

## Critères de classement
Score initial maximal : 100 points.
- Département identique : +40.
- Permission requise présente et non interdite : +25.
- Compétences recoupant la tâche : +15.
- Objectifs recoupant la tâche : +10.
- Rôle recoupant la tâche : +10.
- Charge actuelle : -2 points par tâche, plafonné à -20.

Les résultats sont départagés par score décroissant, puis charge croissante, puis identifiant d'agent. Chaque résultat fournit les raisons du score.

## Éligibilité stricte
- Agent déclaré actif.
- Carte d'identité unique, active et complète.
- Permissions et interdictions identiques au registre des agents.
- Permission requise présente et non interdite.
- Si `assigner_id` est fourni, l'agent doit être un subordonné direct du responsable.

Les agents planifiés, incomplets ou présentant une divergence de permissions sont exclus, et non simplement pénalisés.

## Utilisation

```python
from papi_core.task_routing import recommend_assignees

recommendations = recommend_assignees(
    task,
    agents=agents,
    identity_registry=identity_registry,
    workload_by_agent={"agent-id": 3},
    assigner_id="manager-agent-id",
)
```

## Limites et sécurité
- Une recommandation n'est pas une affectation : l'affectation doit ensuite passer par `assign_task` et le stockage transactionnel.
- Le module ne modifie aucun registre et ne lance aucun agent.
- Il n'infère pas de disponibilité réelle : la charge transmise est un instantané fourni par l'appelant.
- Les compétences et objectifs des cartes actuelles sont souvent vides ou provisoires. Le classement ne devient pertinent qu'après leur validation.
- Les agents PAPI présents dans les registres ne sont pas activés par ce module.
