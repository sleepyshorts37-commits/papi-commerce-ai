# Mission 17 — Jour 2/5 : adaptateurs de sources en lecture seule

## Livré
- Parser RSS 2.0 et parser JSON API avec contrat conservateur.
- Normalisation des résultats en candidats non vérifiés.
- Signalement explicite des champs manquants nécessaires à la qualification.
- Limites de taille et de nombre d'éléments.
- Rejet des URL non HTTPS et des DTD/entités XML.
- Tests unitaires et documentation de sécurité.

## Non livré / hors périmètre
- Pas de collecte réseau, de scraping, de connexion à des plateformes ou de stockage de clés.
- Aucun flux externe n'est déclaré autorisé sans vérification de ses conditions.
- Pas de candidature ni d'action sur un compte utilisateur.

## Critères d'acceptation
- Payload RSS/JSON valide transformé en candidats non vérifiés.
- Données malformées, URL dangereuses, XML avec DTD et payloads surdimensionnés rejetés.
- Les informations inconnues restent inconnues ; aucune rémunération ou éligibilité n'est inventée.
