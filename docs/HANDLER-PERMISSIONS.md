# Registre de handlers et permissions

## Objectif
La file de travaux ne doit jamais exécuter du code fourni dans un payload. Chaque handler doit être enregistré explicitement dans le code, avec une classe d'action connue.

## Barrières appliquées
1. Le nom du handler doit exister dans le registre Python et dans `config/policy.json`.
2. `execution_enabled` doit être explicitement activé.
3. La tâche doit être au statut `in_progress`.
4. Une tâche marquée `approval_required` doit avoir une approbation positive.
5. La classe d'action doit être activée dans `action_permissions`.
6. Les communications externes, opérations financières et actions juridiques restent bloquées tant que l'approbation et `external_actions_enabled` ne sont pas explicitement configurés.

## Mode actuel
L'exécution est désactivée. Les handlers `internal.echo` et `report.preview` sont uniquement des noms autorisés à titre de démonstration ; aucun handler de production, email, réseau social, paiement ou fournisseur n'est connecté.

## Exemple de handler local
```python
from papi_core.handler_registry import HandlerRegistry, execute_authorized_job

registry = HandlerRegistry()
registry.register(
    "internal.echo",
    "read_only",
    lambda payload, context: {"received_keys": sorted(payload.keys())},
)
```

L'appel à `execute_authorized_job` échoue tant que la politique ne permet pas l'exécution. Le registre n'importe jamais de module et n'évalue jamais de code venant du job.

## Limites
Ce contrôle est une barrière applicative, pas un sandbox. Avant tout déploiement, il faudra isoler les workers, limiter leurs accès système et réseau, définir des quotas, surveiller les journaux et tester la politique sur l'environnement hébergé. Aucun worker n'est déployé actuellement.
