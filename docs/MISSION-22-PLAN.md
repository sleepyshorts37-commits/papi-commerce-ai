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

## Jours suivants — critères de sortie prévus

1. Exécuter les migrations et tests de permissions/RLS sur un environnement Supabase local complet.
2. Tester les adaptateurs mémoire et PAPI CHAT sur PostgREST réel, notamment idempotence, pagination et cloisonnement.
3. Produire un rapport de préparation, les limites restantes et les conditions de validation humaine.

## Garde-fous

- Aucun secret service_role dans le dépôt, les logs, les artefacts ou un client.
- Aucun test contre un projet hébergé sans autorisation explicite du propriétaire.
- Aucun transfert de mémoire locale, aucune fusion, suppression ou écriture automatique entre instances.
- Aucun merge ni déploiement sans autorisation explicite.
