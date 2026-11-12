# PAPI TASK DELEGATION SYSTEM — Phase 1.21

## Objectif
Préparer des propositions de délégation interne entre agents, en contrôlant les identités, les statuts, les permissions et la relation hiérarchique.

## Contrôles
- Délégant et destinataire doivent exister dans les deux registres, être actifs/déployés et posséder un profil complet.
- Le délégant doit disposer explicitement de `delegate_internal_tasks`, sans interdiction correspondante.
- Si le destinataire possède un `manager_id`, seul ce responsable direct peut lui proposer une délégation.
- Identifiants, priorité, sujet, instructions et date facultative sont validés.
- Les contenus comportant des coordonnées e-mail/téléphone sont refusés.
- Les propositions explicites `task.delegation.proposed` sont projetées dans le centre de délégation en lecture seule.

## Limites
- Une proposition n'est pas une affectation : aucune modification de `tasks.json`, aucune notification, aucun démarrage de worker.
- Aucune permission ou identité n'est modifiée.
- L'approbation du propriétaire n'est pas authentifiée et aucune décision n'est appliquée.
- L'authentification cryptographique runtime n'est pas disponible.
- Les agents actuellement planifiés/incomplets seront refusés, comme prévu par le principe de refus par défaut.

## Vérification
Tests ajoutés dans `tests/test_task_delegation.py`. Ils n'ont pas été exécutés ici ; CI à vérifier.
