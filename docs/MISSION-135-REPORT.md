# Mission 135 — Import iPhone vers PostgreSQL et worker éditorial

## Livrables
- L'endpoint WSGI accepte maintenant un callback serveur optionnel de persistance PostgreSQL.
- À la réception, le manuscrit est d'abord écrit dans le volume privé ; le callback enregistre ensuite le livre et le job dans une transaction PostgreSQL.
- Si PostgreSQL est indisponible, l'API répond HTTP 503 avec une référence de dépôt et un indicateur de reprise. Le manuscrit reste privé ; une nouvelle requête identique relance l'enregistrement au lieu de perdre le travail.
- Le statut de persistance et les identifiants PostgreSQL sont écrits atomiquement dans metadata.json.
- Fabrique de callback intégrée à l'adaptateur PostgreSQL, sans lecture de secret ni connexion réseau implicite.
- Worker supervisable qui réclame un job avec lease, exécute uniquement l'analyse déterministe locale, enregistre le résultat et l'audit, ou programme un retry.
- Tests couvrant reprise d'enregistrement après indisponibilité DB, worker idle, succès hors ligne et retry.

## Limites / sécurité
- Le callback doit être injecté par l'application WSGI à partir d'une factory DB-API serveur ; il n'est pas activé par défaut.
- Le worker n'appelle ni LLM, ni API image, ni fournisseur payant.
- Aucun secret, aucune connexion réelle, aucune dépense, aucun déploiement, aucune publication.
- Les migrations de la PR 134 restent non appliquées au projet Supabase actif.
- Les fichiers manuscrits restent sur le volume privé ; les métadonnées, états, jobs et événements sont dans PostgreSQL lorsque le callback est configuré.

## Activation
Après revue et fusion explicites des PR dépendantes, appliquer la migration approuvée, injecter la factory DB-API côté serveur, passer le callback à \`create_papi_kids_manuscript_app\`, puis exécuter le worker sous supervision avec un identifiant distinct par instance.
