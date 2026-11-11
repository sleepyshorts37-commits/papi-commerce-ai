# Planificateur et automatisations PAPI

## Rôle
Le planificateur lit des définitions récurrentes et calcule les échéances à examiner. Il sépare le calendrier de l'exécution des tâches.

## Formats pris en charge
- `daily` : chaque jour à une heure locale.
- `weekly` : certains jours ISO (0=lundi, 6=dimanche).
- Fuseau horaire IANA obligatoire, par exemple `Africa/Dakar`.
- `enabled=false` par défaut dans le registre initial.
- `last_run_at` empêche une deuxième échéance le même jour.

## Utilisation
```python
from datetime import datetime
from zoneinfo import ZoneInfo
from papi_core.scheduler import due_schedules

due = due_schedules(now=datetime.now(ZoneInfo("Africa/Dakar")))
print(due)
```

La commande CLI est `PYTHONPATH=runtime python -m papi_core schedule-preview`.

## Garde-fous
- Le planificateur ne démarre aucun worker et n'enfile aucune tâche.
- Les échéances sont des propositions `awaiting_scheduler_review`, pas des exécutions.
- Les handlers doivent être contrôlés par la politique et le registre d'autorisations existants.
- Toute communication externe, dépense, action financière ou juridique reste interdite sans autorisation explicite du propriétaire.
- Aucun service payant, clé API, connexion Supabase ou modèle IA n'est requis pour cette brique.

## Limites
Pas de processus permanent, cron, GitHub Actions planifié, service hébergé, verrou multi-instance, rattrapage de plusieurs jours ou déclenchement autonome. Le déploiement et l'authentification des acteurs restent à construire.

## Statut
Moteur local de calcul d'échéances et tests ajoutés ; aucune automatisation récurrente n'est active.
