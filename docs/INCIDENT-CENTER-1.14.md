# PAPI INCIDENT CENTER 1.14

## Objectif
Construire une vue centralisée des incidents à partir du journal d'audit append-only existant.

## Événements supportés
- `incident.reported` : déclaration avec severity, category, summary et recommendation.
- `incident.acknowledged` : prise en charge.
- `incident.resolved` : résolution documentée.

Les événements doivent cibler `entity_type=incident`. L'identifiant d'incident est `entity_id`. Les transitions sont ajoutées au journal ; aucun événement existant n'est modifié ou supprimé.

## Catégories et gravités
Gravités : info, warning, critical.
Catégories : worker, job, security, platform, data, integration, other.

## Sécurité et limites
Projection strictement en lecture seule. Aucun envoi de notification, aucune action externe, aucune modification du journal, aucun redémarrage ou retry. Les transitions invalides sont rejetées. Les événements non liés aux incidents sont ignorés. Le centre ne crée pas automatiquement des incidents à partir des erreurs runtime : un composant autorisé devra enregistrer explicitement un événement incident.reported.
