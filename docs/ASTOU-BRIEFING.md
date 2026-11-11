# Briefing de direction — Astou

Le module `papi_core.astou` produit un briefing déterministe à partir des registres locaux des agents, des tâches et de la politique.

## Utilisation

Depuis la racine du dépôt :

```bash
PYTHONPATH=runtime python -c "import json; from papi_core.astou import build_director_brief; print(json.dumps(build_director_brief(), ensure_ascii=False, indent=2))"
PYTHONPATH=runtime python -m unittest discover -s tests -v
```

## Contenu du briefing

- Faits mesurables : nombre d'agents, nombre d'agents actifs déclarés et tâches par statut.
- Escalades propriétaire : tâches nécessitant une approbation encore absente.
- Tâches à examiner : tâches ouvertes dont le responsable n'existe pas dans le registre.
- Recommandations opérationnelles calculées à partir de ces constats.

## Limites

Le rapport est local, déterministe et en lecture seule. Il ne prouve pas qu'un agent est réellement déployé, ne contacte aucun service, n'affecte aucune tâche et ne lance aucun agent IA. Les autorisations de la politique restent prioritaires.
