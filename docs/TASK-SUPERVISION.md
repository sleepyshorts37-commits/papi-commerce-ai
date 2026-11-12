# PAPI TASK SUPERVISION 0.5 — détection proactive des risques

## Objectif
Le module `papi_core.supervision.supervise_tasks` examine les missions ouvertes et classe les risques à partir de règles déterministes.

## Facteurs
- Mission bloquée : +45.
- Responsable absent ou inconnu : +35.
- Échéance dépassée : +40.
- Échéance dans la fenêtre configurée : +20.
- Dernière mise à jour (ou création si aucune mise à jour) antérieure au seuil : +20.
- Approbation requise mais non approuvée : +15.
- Priorité haute : +10; urgente : +15.

Sévérité : critical à partir de 70; high à partir de 40; medium à partir de 20; low en dessous. Le score est un indicateur de tri, jamais une probabilité.

## Utilisation
```python
from papi_core.supervision import supervise_tasks

report = supervise_tasks(
    tasks,
    agents=agents,
    as_of="2026-11-12T08:00:00Z",
    due_soon_hours=24,
    stale_after_hours=48,
)
```

## Garde-fous
- Analyse en lecture seule, sans notification ni affectation.
- Les seuils sont explicites et configurables par appel.
- Les dates doivent inclure un fuseau horaire.
- L'absence de date ne constitue pas une preuve d'inactivité.
- L'outil ne lance pas Astou comme agent autonome; il fournit une fonction de supervision intégrable.
