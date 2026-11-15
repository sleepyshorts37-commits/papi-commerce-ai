# Mission 132 — Réception authentifiée des manuscrits

## Endpoint
WSGI POST /api/papi-kids/manuscripts. Le client transmet le texte UTF-8 brut, un nom de fichier .md ou .txt, et un jeton Bearer dans l'en-tête Authorization.

## Sécurité
- HTTPS obligatoire (sauf option de test local explicitement injectée).
- Jeton serveur PAPI_KIDS_UPLOAD_TOKEN de 32 caractères minimum ; comparaison à temps constant.
- Taille maximale : 2 Mio ; UTF-8 uniquement ; noms de fichiers filtrés.
- Stockage privé sur le volume serveur, permissions restrictives, identifiant aléatoire, empreinte SHA-256.
- Aucun contenu du manuscrit ou secret dans la réponse API.

## Limites
Le module WSGI doit être monté par l'application/hébergeur et le secret ainsi que le volume privé configurés côté serveur. Cette PR ne déploie rien. L'état initial est received_pending_editorial_analysis : aucun traitement IA automatique n'est déclenché par l'upload.
