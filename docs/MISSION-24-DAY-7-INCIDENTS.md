# Mission 24 — Jour 7 : gestion des incidents

## Classification
- **SEV-1 — Critique :** compromission présumée, accès non autorisé, corruption ou perte de données, exposition de secrets. Isoler le composant concerné et escalader immédiatement au responsable humain.
- **SEV-2 — Majeur :** file bloquée, accumulation importante, indisponibilité durable du service de données. Geler les changements et préparer un diagnostic.
- **SEV-3 — Modéré :** hausse de retries/échecs ou latence anormale sans perte confirmée. Examiner les agrégats et comparer aux références connues.
- **SEV-4 — Mineur :** anomalie ponctuelle sans impact utilisateur identifié. Documenter et suivre.

## Arbre de décision
1. Confirmer l'environnement et l'heure de début.
2. Consulter uniquement les agrégats de santé et le résumé d'erreurs.
3. Si suspicion de fuite ou d'accès abusif : traiter comme SEV-1, préserver les éléments autorisés et révoquer les accès par un opérateur habilité.
4. Si PostgreSQL est indisponible : ne pas lancer de reprise concurrente ; vérifier l'état de l'infrastructure via le canal d'exploitation autorisé.
5. Si des baux sont expirés ou la file s'accumule : demander une analyse humaine avant toute action.
6. Consigner décision, responsable, approbation et résultat.

## Journalisation sûre
Enregistrer horodatage, identifiant d'incident interne, sévérité, composant, compteurs agrégés, décision et approbateur. Ne jamais copier payload, résultat de tâche, jeton de bail, secret, données personnelles ou code d'erreur interne dans le ticket général.

## Modèle d'alerte interne (à envoyer manuellement)
Titre : [SEV-x] [composant] — [symptôme bref]
Début : [UTC]
Impact observé : [description non sensible]
Mesures agrégées : [compteurs autorisés]
Actions déjà réalisées : [faits]
Décision/approbateur : [nom/fonction et heure]
Prochaine revue : [heure]

Aucune notification n'est envoyée automatiquement. Aucun scheduler ou canal externe n'est configuré.
