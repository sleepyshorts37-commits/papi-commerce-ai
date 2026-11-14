# Mission 28 — PAPI WORKER ENGINE

## Jour 1 — Architecture
Définir le cycle de vie worker, les responsabilités hiérarchiques, le contrat de tâche, les états dormants et les limites de sécurité.

## Jour 2 — Registre des agents
Créer un registre avec identité immuable, département, rôle, responsable, compétences, permissions, statut et capacité. L'enregistrement ne vaut pas activation.

## Jour 3 — Distribution
Créer une attribution transactionnelle qui vérifie statut actif, compétence, permission, capacité et unicité de tâche. Créer le job interne dans la même transaction.

## Jour 4 — Exécution
Permettre au worker autorisé de réclamer uniquement ses jobs. Utiliser un bail et un jeton de fencing. Mettre à jour job et affectation ensemble. Rejeter les complétions d'un autre worker ou d'un bail expiré.

## Jour 5 — Validation
Tester enregistrement dormant, activation explicite, permission, capacité, idempotence, tâche déjà attribuée, claim et complétion. Vérifier les permissions SQL et la CI.

## Gouvernance
Toutes les fonctions sont réservées au backend de confiance (service_role). Aucun worker n'est activé à l'enregistrement. Aucun appel externe, paiement, publication, message ou déploiement n'est déclenché. Les workers n'ont aucun droit SQL direct. La hiérarchie est enregistrée mais les changements hiérarchiques doivent rester contrôlés par un administrateur de confiance.
