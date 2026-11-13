# Revue finale de préparation — phase du 13 novembre 2026

## Résultat exécutif

Cette revue couvre les PR #102, #103, #104, #106 et #107 ainsi que les validations GitHub Actions observées sur la tête de #107.

**Décision : validation technique de la branche #107 réussie ; pas d'autorisation de mise en production.** Les contrôles automatisés réussis ne remplacent ni une revue de sécurité indépendante, ni une validation sur une infrastructure de préproduction, ni la vérification des dépendances empilées.

## État des PR et dépendances

- #102 : ouverte, brouillon, non fusionnée ; base déclarée `feat/durable-job-attempt-ids-2026-11-17` (PR #101 à examiner dans la revue globale).
- #103 : ouverte, brouillon, non fusionnée ; base `integration/security-approval-audit-2026-11-13`. Cette branche est parallèle et n'est pas ancêtre de la chaîne #102 → #104 → #106 → #107.
- #104 : ouverte, brouillon, non fusionnée ; empilée sur #102.
- #106 : ouverte, brouillon, non fusionnée ; empilée sur #104.
- #107 : ouverte, brouillon, non fusionnée ; empilée sur #106.
- #105 : PR dupliquée/fermée ; ne pas réactiver.

Les branches empilées doivent être revues et intégrées dans l'ordre des dépendances par un mainteneur humain. La PR #103 exige une décision d'intégration séparée avant qu'on puisse considérer l'ancrage externe comme faisant partie du produit intégré.

## Validation CI — tête exacte de #107

SHA examiné : `c819669e21263247647d663449b196a16872ac54`.

- Workflow `PAPI core tests — attempt audit`, run 43425062028 : **success**. Étapes réussies : tests unitaires, application du schéma Supabase à PostgreSQL jetable, historique des tentatives, claims concurrents avec SKIP LOCKED, crash recovery/idempotency/classification, rollback de migration des tentatives.
- Workflow `PAPI registry validation`, run 43425062061 : **success**.
- Workflow `PAPI documentation checks`, run 43425062435 : **success**.

Les trois runs correspondent au SHA exact de la tête #107. Le statut combiné ne renvoyait pas de checks supplémentaires.

## Capacités validées dans les scénarios testés

- Identifiants d'essai durables et audit corrélé par tentative.
- Classification des erreurs réessayables et terminales, et simulation d'arrêt brutal.
- Réservation concurrente de jobs distincts avec `FOR UPDATE SKIP LOCKED`.
- Renouvellement et complétion conditionnels au propriétaire et au jeton de bail ; rejet d'un worker obsolète dans les scénarios SQL testés.
- Délégation bornée par la hiérarchie directe et les permissions du délégant et du délégataire ; refus des cycles, identités inactives, auto-délégations et permissions dupliquées.
- Les contrôles de délégation ne modifient pas le registre et ne donnent pas de droits réels.

## Réserves de sécurité et de production

### 1. Ancrage externe (#103) — non intégré à la chaîne principale

- L'adaptateur Supabase appelle la méthode privée `SupabaseStore._request` : couplage interne à stabiliser avant une intégration durable.
- La RPC SQL vérifie le digest, les champs de l'enveloppe, le lien au digest précédent et le compare-and-swap sous verrou. Elle vérifie seulement que `signature` et `key_id` sont présents ; elle ne vérifie pas cryptographiquement la signature. La validation cryptographique reste donc à la charge du protocole applicatif et n'est pas une preuve indépendante côté base.
- Le test SQL utilise une signature littérale `test-only` : il valide le stockage et l'avancement du pointeur, pas l'authenticité cryptographique.
- Le schéma ajoute les tables et la RPC, mais la PR ne fournit pas de migration dédiée up/down pour cette fonctionnalité. Préparer une migration versionnée et son rollback contrôlé avant déploiement.
- Les tests PostgreSQL sont jetables ; aucun projet Supabase réel, secret, politique de sauvegarde/restauration ou publication distante n'a été testé.

### 2. Exécution des workers (#102/#104/#106)

- Le modèle est à reprises avec bail, pas exactly-once. Un effet métier peut être répété après crash survenu après l'effet et avant la complétion.
- Les handlers doivent utiliser des clés d'idempotence métier stables et vérifier le bail avant les étapes sensibles.
- Les tests couvrent des scénarios simulés et PostgreSQL jetable ; ils ne prouvent pas le comportement de tous les fournisseurs externes ni les pannes réseau réelles.

### 3. Identité et gouvernance (#107)

- La délégation est un reçu `authorized_for_review`, pas une permission persistée, révocable ou exécutoire.
- L'identité fournie au runtime doit encore être liée à une authentification de service vérifiable ; un identifiant transmis n'est pas à lui seul une preuve cryptographique.
- La journalisation transactionnelle des changements de registre, l'expiration des délégations et la révocation fortement cohérente restent à construire avant activation multi-agent.

### 4. Ordre de fusion et CI

- Les résultats CI de #107 valident la tête #107 et sa chaîne d'ancêtres déclarée, mais ils ne valident pas l'intégration de la branche indépendante #103.
- Les PR #102–#107 sont toutes encore brouillon/non fusionnées au moment de la revue. Leur état doit être revérifié juste avant toute décision humaine.
- Ne pas fusionner en lot ni sauter une dépendance. Refaire les checks sur les SHA résultant de chaque intégration.

## Garde-fous maintenus

Aucun merge, déploiement, migration sur une base réelle, worker/agent réel activé, secret de production créé, contact externe ou opération financière n'a été effectué dans cette phase.

## Conditions minimales avant production

1. Examiner la PR #101 et résoudre les dépendances de la chaîne #102 → #104 → #106 → #107.
2. Décider explicitement si et comment #103 rejoint la chaîne ; ajouter migration up/down dédiée.
3. Ajouter une vérification cryptographique de signature indépendante et des tests de clés, rotation, révocation et restauration.
4. Remplacer le couplage à `_request` par une interface de stockage publique/stable.
5. Ajouter tests d'intégration de pannes réseau, perte de bail et reprise avec un fournisseur sandbox.
6. Implémenter authentification de workload, audit transactionnel du registre, expiration/révocation des délégations et contrôles serveur.
7. Réaliser revue indépendante de sécurité, sauvegarde/restauration et plan de rollback en préproduction.

**Conclusion :** les tests automatisés de la chaîne #107 sont verts sur son SHA exact. Le produit demeure en état de développement contrôlé ; les réserves ci-dessus empêchent de qualifier cette phase de prête pour la production.
