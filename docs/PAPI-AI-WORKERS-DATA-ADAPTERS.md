# PAPI AI WORKERS — adaptateurs de données vers COMMAND CENTER

## Mission 20 — Jour 2/5

### Objectif
Définir un contrat explicite pour transmettre au tableau de bord les sorties des trois modules PAPI AI WORKERS : découverte de plateformes, relais humain et rentabilité.

### Adaptateurs
Le module papi_core.workers_inputs expose build_workers_inputs :
- platform_discovery_batch : lot de découverte contenant une liste results ;
- handoff_records : liste de dossiers issus du relais humain ;
- profitability_batch : lot de classement économique contenant une liste results.

Les structures sont vérifiées avant transmission à build_workers_report. Une source absente est distinguée d’une source explicitement fournie mais vide. Les collections normalisées du Jour 1 restent prises en charge ; fournir simultanément les deux formes pour une même source est interdit.

### Traçabilité et limites
La sortie ai_workers_sources indique quelles sources ont été fournies. Elle précise explicitement que la collecte automatique, la lecture d’un stockage persistant et l’accès réseau n’ont pas eu lieu.

Cette étape ne réalise pas de collecte automatique, ne lit aucun registre persistant, ne contacte aucune plateforme et ne déclenche aucun worker, scheduler, notification ou action financière. Les données doivent être passées explicitement par l’appelant et restent soumises aux validations métier et à une revue humaine.

### Tests
- Formats de lot et listes acceptés ou rejetés.
- Sources absentes distinguées des sources vides.
- Intégration des formes de sortie des trois domaines dans COMMAND CENTER.
- Rejet des entrées ambiguës.
- Maintien des garde-fous sans action externe.
