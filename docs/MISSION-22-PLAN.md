# Mission 22 — Validation d'intégration Supabase

## Objectif

Passer des contrats simulés de la Mission 21 à une validation reproductible de la frontière HTTP/PostgREST, puis préparer des tests d'intégration sur un environnement Supabase local/éphémère explicitement contrôlé. Cette mission n'active aucune synchronisation automatique.

## Jour 1/5 — Contrat HTTP de l'adaptateur partagé

- Tests traversant SupabaseStore._request et SharedCollaborationStore, avec transport intercepté à la frontière.
- Vérification des URL/méthodes PostgREST, en-têtes serveur, filtres destinataires, idempotence et erreurs sans divulgation de secrets.
- Aucun projet hébergé ni secret réel.

## Jour 2/5 — Harnais PostgreSQL jetable

- Ajout d'un Compose PostgreSQL 16 reproductible, isolé sur loopback et stockage éphémère.
- Création de rôles de test anon, authenticated et service_role.
- Procédure documentée pour appliquer deux fois le schéma et les migrations partagées.
- Limite explicitée : PostgreSQL seul ne valide ni Supabase Auth, ni PostgREST, ni les JWT.

## Jour 3/5 — PostgREST local réel

- PostgREST v12.2.12 devant PostgreSQL jetable.
- JWT HS256 local, insertion, filtre destinataire et protection append-only.
- Limite : aucun Supabase Auth ni gateway complet.

## Jour 4/5 — Adaptateurs applicatifs réels

- Tests des adaptateurs mémoire partagée et PAPI CHAT via PostgREST local.
- Vérification idempotence, lecture filtrée et pagination.
- CI dédiée sur la pile locale jetable.

## Jour 5/5 — Frontière d'authentification et rapport de préparation

- Matrice de rejet des requêtes sans jeton, malformées, signées avec une mauvaise clé, expirées et portant le rôle anon.
- Conservation des tests d'insertion privilégiée, de cloisonnement et d'immutabilité.
- Rapport final distinguant les contrôles validés localement des composants non couverts.

## Garde-fous

- Aucun secret service_role dans le dépôt, les logs, les artefacts ou un client.
- Aucun test contre un projet hébergé sans autorisation explicite du propriétaire.
- Aucun transfert de mémoire locale, aucune fusion, suppression ou écriture automatique entre instances.
- Aucun merge ni déploiement sans autorisation explicite.
