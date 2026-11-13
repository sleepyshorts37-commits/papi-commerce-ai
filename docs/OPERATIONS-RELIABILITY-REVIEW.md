# Revue opérationnelle — fiabilité et reprise

## Périmètre vérifié
Cette revue couvre les contrats du dépôt : registre de migrations offline, évaluateur de santé, validation de sauvegarde/restauration, politique de reprise, worker à exécution unique et file à bail. Elle ne constitue pas une recette d'environnement de production.

## Matrice de vérification

| Domaine | Contrat vérifiable | Contrôle | Limite restante |
|---|---|---|---|
| Migrations | Inventaire ordonné, empreintes et fichiers cohérents | Validateur offline + CI | Aucune migration appliquée à une base réelle |
| Monitoring | États healthy/degraded/unavailable/unknown et fraîcheur | Tests unitaires sur snapshots injectés | Aucune sonde réseau ni alerte active |
| Sauvegarde | Manifeste, empreintes, chemins sûrs, plan de restauration | Tests offline | Pas de sauvegarde réelle ni exercice de restauration |
| Retry | Erreurs transitoires typées, plafond durable, backoff et jitter injecté | Worker et RPC raccordés ; claim renvoie le plafond persisté ; tests Python et PostgreSQL jetable | Validation distante, observabilité retry et jitter runtime à compléter |
| Queue | Clé d'idempotence, bail et transitions contrôlées | Tests du dépôt et PostgreSQL jetable | Aucun test contre un projet Supabase distant |
| Worker | Authentification, approbation, renouvellement de bail, audit | Tests unitaires avec dépendances contrôlées | Pas de service permanent ni de test multi-worker en production |

## Critères d'acceptation de cette phase
- Les validations de documentation, registre et tests principaux passent sur le SHA exact de la PR finale.
- Les tests de base de données utilisent uniquement PostgreSQL jetable.
- Les erreurs permanentes ne sont pas réessayées par défaut ; les erreurs transitoires ont un plafond strict.
- Aucun handler n'est démarré sans autorisation et bail valide.
- Aucun comportement de production n'est activé par cette PR.

## Points à résoudre avant toute mise en production
1. Valider le comportement de reprise sur un projet Supabase isolé et ajouter métriques/alertes pour les tentatives, erreurs et épuisements de plafond.
2. Tester les courses multi-workers, expiration de bail, fencing et reprise après crash avec PostgreSQL isolé.
3. Exécuter un exercice de sauvegarde/restauration avec stockage et secrets gérés, puis mesurer RPO/RTO réels.
4. Ajouter des sondes, alertes, métriques, rétention et astreinte opérationnelles.
5. Valider l'identité de service, la signature, les clés et les contrôles d'accès dans l'environnement cible.
6. Faire réaliser une revue de sécurité indépendante et une recette humaine documentée.

## Décision
**NO-GO production.** Les contrôles de dépôt améliorent la vérifiabilité mais ne prouvent ni disponibilité réelle, ni restauration opérationnelle, ni absence de doublons d'effets externes. La livraison reste une préparation contrôlée, sans déploiement ni exécution de workers.
