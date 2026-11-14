# Mission 22 — Rapport de préparation sécurité

**Périmètre :** tests locaux jetables PostgreSQL 16 + PostgREST 12.2.12.  
**État :** validation de code et CI locale ; aucune validation de projet Supabase hébergé.

## Contrôles validés par la suite automatisée

- Contrat HTTP des adaptateurs et gestion des erreurs sans divulgation de secrets.
- PostgreSQL : application répétée des migrations, contraintes d'idempotence, privilèges de rôles et refus des mutations append-only.
- PostgREST local : authentification JWT HS256 de test, insertion autorisée, lecture filtrée par destinataire et refus de PATCH.
- Adaptateurs applicatifs : mémoire partagée et PAPI CHAT, avec idempotence, filtrage et pagination.
- Jour 5 : tentatives sans jeton, avec jeton malformé, mauvaise clé de signature, jeton expiré et rôle anon.

## Limites explicites

Les tests ne démontrent pas le fonctionnement d'un environnement Supabase hébergé. Ils ne valident pas Supabase Auth, Kong/API Gateway, les flux de rafraîchissement de session, Storage, Realtime, les politiques réseau, les sauvegardes, la supervision ni les secrets d'un projet réel. Le JWT utilisé est un jeton de test local et ne doit jamais être réutilisé en production.

## Conditions avant toute mise en production

1. Créer un environnement Supabase de préproduction autorisé et isolé.
2. Configurer Auth, les rôles et les politiques RLS avec des identifiants dédiés.
3. Rejouer les tests avec des comptes anon/authenticated réels et des scénarios d'accès croisés.
4. Vérifier les journaux, la rotation des secrets, les sauvegardes et la procédure de restauration.
5. Faire examiner les résultats et obtenir une approbation humaine explicite avant toute activation.

## Gouvernance

Aucune synchronisation automatique inter-instance n'est activée. Aucun transfert, retrait, paiement, merge ou déploiement n'est autorisé par cette mission. Les secrets de service ne doivent jamais être exposés au navigateur ou à un agent non autorisé.
