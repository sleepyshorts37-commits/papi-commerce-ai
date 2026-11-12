# Affectation contrôlée des tâches — PAPI TASK ENGINE 0.1

## Capacité ajoutée
Le module `papi_core.task_assignment` prépare une affectation et son événement d'audit sans modifier le stockage ni lancer un agent.

## Conditions obligatoires
- Le responsable et le destinataire doivent être déclarés actifs.
- Chacun doit posséder exactement une carte d'identité active et complète.
- Les permissions et interdictions de la carte doivent correspondre exactement au registre agents.
- Le responsable doit posséder `assign_internal_tasks`.
- Le destinataire doit dépendre directement du responsable dans `manager_id`.
- Une tâche terminée ou annulée ne peut pas être réaffectée.
- Si `required_permission` est défini sur la tâche, le destinataire doit la posséder.

## Exemple
```python
from papi_core.task_assignment import assign_task

updated_task, audit_event = assign_task(
    task,
    assigner_id="manager-agent-id",
    assignee_id="worker-agent-id",
    agents=agents,
    identity_registry=identity_registry,
)
```

L'appelant doit authentifier cryptographiquement l'acteur avant d'appeler ce module, puis persister la tâche et l'événement dans une transaction atomique avec le stockage. Le module ne prétend pas authentifier un processus, ne persiste rien et ne déclenche aucune exécution.

## Tests
`PYTHONPATH=runtime python -m unittest discover -s tests -p 'test_task_assignment.py' -v`

Les identités actuelles du dépôt sont encore planifiées/incomplètes : aucune affectation réelle à un agent n'est donc autorisée à ce stade.

## Intégration Supabase — version 0.2

`SupabaseStore.assign_task_and_save(...)` relit la tâche et vérifie sa version attendue, prépare l'affectation, puis appelle `papi_commit_task_change`. Cette fonction PostgreSQL met à jour la tâche et insère l'événement d'audit dans une seule transaction. Un conflit de version ou une affectation refusée ne produit aucune écriture.

Exemple :

```python
updated_task, new_version = store.assign_task_and_save(
    task_id,
    assigner_id=authenticated_agent_id,
    assignee_id=target_agent_id,
    agents=agents,
    identity_registry=identity_registry,
    expected_version=current_version,
)
```

**Frontière de sécurité :** le service de stockage ne remplace pas l'authentification Ed25519 de l'acteur. Le backend doit vérifier la signature et les droits de l'acteur avant d'appeler cette méthode. Le secret Supabase reste côté serveur. Aucun worker n'est démarré.
