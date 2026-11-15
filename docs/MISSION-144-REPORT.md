# Mission 144 — Bibliothèque multi-livres sur iPhone

## Livrables
- Lecteur PostgreSQL serveur qui renvoie les 50 projets les plus récents, sans contenu manuscrit ni chemin privé.
- Résumé par livre : titre/nom source, statut éditorial, état du job, tentatives, nombre d'illustrations et nombre approuvé.
- Endpoint GET \`/api/papi-kids/manuscripts\`, HTTPS et jeton Bearer.
- Tableau de bord iPhone : bibliothèque, actualisation, progression des illustrations et bouton pour ouvrir le suivi détaillé.
- Après un dépôt, la bibliothèque se rafraîchit automatiquement avant d'effacer le jeton du champ.
- Tests hors réseau pour l'endpoint, le lecteur DB et l'affichage.

## Sécurité
Le navigateur n'accède jamais directement à Supabase et ne reçoit ni texte de manuscrit, ni chemin de stockage, ni secret serveur.
