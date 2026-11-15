# Mission 136 — Consultation sécurisée de l'état du livre

## Livrables
- Endpoint GET authentifié par Bearer token pour consulter un dépôt précis.
- Callback de lecture PostgreSQL côté serveur ; la réponse ne contient ni texte du manuscrit, ni nom de fichier, ni secret, ni détail d'erreur interne.
- Statut livre, statut du job, tentatives, maximum de tentatives, dates de création/mise à jour et bail exposés au seul utilisateur possédant le jeton.
- Fabrique de lecteur PostgreSQL dans l'adaptateur DB-API.
- Tableau de bord iPhone : champ de référence et bouton de consultation ; rendu exclusivement via textContent.
- Tests pour accès authentifié, réponse filtrée et fermeture si le lecteur n'est pas configuré.

## Sécurité / limites
- Le lecteur PostgreSQL doit être injecté côté serveur.
- Le statut n'est pas publiquement accessible ; le jeton est exigé en HTTPS.
- Aucun secret ajouté, aucune connexion réelle, aucun appel IA/image, aucun déploiement, aucune dépense.
