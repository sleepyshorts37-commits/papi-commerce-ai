# Mission 22 — Validation d'intégration Supabase

## Objectif

Passer des contrats simulés de la Mission 21 à une validation reproductible de la frontière HTTP/PostgREST, puis préparer des tests d'intégration sur une instance Supabase de test explicitement autorisée. Cette mission n'active aucune synchronisation automatique.

## Jour 1/5 — Contrat HTTP de l'adaptateur partagé

- Ajouter des tests qui traversent réellement `SupabaseStore._request` et `SharedCollaborationStore`, avec le transport réseau remplacé uniquement à la frontière.
- Vérifier la méthode, l'URL PostgREST, les filtres destinataires côté serveur, les en-têtes d'authentification serveur et la préférence d'idempotence.
- Vérifier qu'une erreur HTTP ne révèle ni corps interne de base de données ni clé d'accès.
- N'utiliser aucun projet Supabase hébergé, aucune clé réelle et aucune donnée utilisateur.

## Jours suivants — critères de sortie prévus

1. Définir et documenter un environnement Supabase local/éphémère reproductible, avec versions et démarrage contrôlés.
2. Exécuter les migrations et tests de permissions/RLS sur cet environnement.
3. Tester les adaptateurs mémoire et PAPI CHAT sur PostgREST réel, notamment idempotence, pagination et cloisonnement.
4. Produire un rapport de préparation, les limites restantes et les conditions de validation humaine.

## Garde-fous

- Aucun secret service_role dans le dépôt, les logs, les artefacts ou un client.
- Aucun test contre un projet hébergé sans autorisation explicite du propriétaire.
- Aucun transfert de mémoire locale, aucune fusion, suppression ou écriture automatique entre instances.
- Aucun merge ni déploiement sans autorisation explicite.
