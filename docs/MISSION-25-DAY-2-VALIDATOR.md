# Mission 25 — Jour 2 : validation stricte et portée minimale

## Implémentation
Ajout de `runtime/papi_core/approval_guard.py` avec une fonction pure `authorize_scoped_approval`.

## Contrôles
- Attestation complète et champs de type texte non vides.
- Décision exactement égale à `approved`.
- Approbateur égal à l'identifiant du propriétaire configuré.
- Correspondance exacte de l'identifiant de tâche, du handler et de la classe d'action.
- Tâche au statut `in_progress`.
- Dates ISO avec fuseau horaire obligatoire.

## Limites
Le validateur ne lit aucun fichier, ne contacte aucun service, n'écrit aucune donnée et n'exécute aucun handler. Il ne prouve pas l'identité de l'émetteur : cette preuve relève de la couche d'authentification.
