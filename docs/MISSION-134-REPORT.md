# Mission 134 — File PostgreSQL transactionnelle et workers concurrents

## Livrables
- Migration SQL versionnée pour un schéma privé \`papi_kids_private\` : livres, jobs éditoriaux et événements d'audit.
- Contraintes d'unicité sur le SHA-256 et le couple livre/type de job ; dépôt rejouable sans doublon.
- Fonction PostgreSQL \`claim_editorial_job\` avec verrouillage \`FOR UPDATE SKIP LOCKED\`, bail limité et reprise des baux expirés.
- Adaptateur DB-API sans dépendance réseau imposée : enregistrement atomique livre + job, prise de tâche, validation de bail, succès, échec et retry borné.
- RLS activé sur les trois tables ; schéma non exposé par défaut ; privilèges conditionnels réservés au rôle serveur \`service_role\`.
- Tests hors réseau sur idempotence contractuelle, rollback, prise de tâche, rejet des baux expirés et retry.

## Sécurité et gouvernance
- Aucun secret Supabase dans le code, GitHub ou le navigateur.
- Aucun accès client direct au schéma privé.
- Aucun appel IA/image, aucune publication, aucun achat ou dépense.
- La migration est proposée dans le dépôt uniquement ; elle n'a PAS été appliquée au projet Supabase actif.
- L'adaptateur n'ouvre aucune connexion de lui-même : le backend doit injecter une factory DB-API protégée par les secrets serveur.
- Le stockage binaire des manuscrits demeure dans le volume privé existant ; PostgreSQL conserve les références, empreintes et états.

## Activation requise
1. Revue puis fusion explicite de la PR.
2. Appliquer la migration via le processus de déploiement approuvé.
3. Configurer côté serveur la factory DB-API et les identifiants PostgreSQL/Supabase ; ne jamais utiliser service_role côté iPhone.
4. Basculer l'endpoint d'import sur l'adaptateur PostgreSQL après configuration et test de santé.
5. Exécuter un worker supervisé ; l'analyse structurelle locale reste séparée des traitements IA payants.

## Validation
Les tests unitaires sont exécutés par CI. La migration doit également être validée dans le job PostgreSQL jetable du dépôt avant toute activation.
