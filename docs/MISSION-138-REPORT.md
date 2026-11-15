# Mission 138 — Validation humaine des illustrations

## Livrables
- Endpoint de revue d'asset séparé du jeton d'upload : secret serveur \`PAPI_KIDS_REVIEW_TOKEN\`.
- Identité du réviseur définie côté serveur via \`PAPI_KIDS_REVIEWER_ID\`, jamais fournie librement par le navigateur.
- Décisions permises : \`approved\` ou \`rejected\`, commentaire limité à 1 000 caractères.
- Adaptateur PostgreSQL transactionnel : mise à jour de statut, date et réviseur ; journal append-only des décisions ; anciennes versions approuvées d'une page marquées \`superseded\` lorsqu'une nouvelle version est approuvée.
- GET d'état renvoie la liste des assets, dimensions, versions et statuts, sans exposer les chemins privés.
- Tableau de bord iPhone : boutons Approuver/Refuser, jeton de revue distinct, rafraîchissement après décision.
- Tests hors réseau pour le secret distinct, l'identité serveur et la fermeture si le handler est absent.

## Gouvernance
- Aucun asset n'est approuvé automatiquement.
- Le secret de revue et l'identifiant du réviseur doivent être configurés uniquement côté serveur.
- Aucun appel IA/image, aucun déploiement, aucune dépense ou publication.
