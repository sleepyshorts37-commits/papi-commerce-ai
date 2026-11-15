# Mission 165 — Publication du tableau de bord mobile

## Livrable
- Le WSGI sert réellement le tableau de bord à \`GET /dashboard\` et \`GET /\`.
- Génération serveur depuis des variables non sensibles pour le livre, le titre et la pagination.
- Exige HTTPS ; rejette HTTP (403) et les méthodes non GET (405).
- En-têtes de sécurité : CSP compatible avec le JS/CSS local, no-store, nosniff, frame denial et referrer-policy.
- Aucun jeton serveur injecté dans le HTML.
- Le tableau de bord regroupe import du manuscrit, statut, revue des illustrations, revue de sécurité jeunesse et bibliothèque.

## Limites
L'accès au tableau de bord dépend encore d'un déploiement réel et d'un reverse proxy HTTPS configuré pour transmettre le schéma HTTPS au WSGI. Aucun déploiement n'a été effectué.
