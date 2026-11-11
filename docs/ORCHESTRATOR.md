# Orchestrateur PAPI — planification consultative

## Objectif
Le module `papi_core.orchestrator` lit le registre des tâches et celui des agents, puis produit une proposition de priorisation et de candidats par département.

## Commande
```bash
PYTHONPATH=runtime python -m papi_core plan
```

## Garanties actuelles
- Lecture seule : aucun fichier n'est modifié.
- Tri déterministe : priorité urgente, haute, normale, basse, puis date et identifiant.
- Une approbation requise mais absente bloque la proposition.
- Un agent n'est considéré comme déployé que si son statut vaut explicitement `active`.
- Les agents actuellement définis comme `defined` ou `planned` ne sont pas exécutés.
- Aucune publication, prospection, dépense, transaction ou communication externe.
- Le plan contient toujours `dispatch_allowed: false` tant que le runtime d'agents n'est pas déployé.

## Limites
Ce composant n'est pas un système multi-agents autonome. Il ne fournit ni mémoire persistante, ni moteur LLM, ni ordonnanceur permanent, ni messagerie inter-agents. Il prépare une décision vérifiable pour une future couche d'exécution.

## Étapes suivantes
1. Valider les transitions d'état et conserver un journal d'audit.
2. Ajouter une persistance contrôlée des tâches.
3. Connecter un moteur d'agents uniquement après validation des coûts, permissions et tests.
