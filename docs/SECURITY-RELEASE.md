# Sécurité et préparation au déploiement

## État actuel
Le contrôle de sécurité est local, déterministe et en lecture seule. Il vérifie que l'exécution des agents, les actions externes et le budget restent désactivés/nuls, que les permissions de communication/finance/juridique sont fermées, que les interdictions fondamentales sont présentes et que les fichiers .env sont ignorés par Git.

## Avant toute mise en service
1. Choisir un environnement d'hébergement compatible avec le budget et les exigences de disponibilité.
2. Créer les comptes de service au nom du propriétaire et activer MFA.
3. Stocker les secrets dans le gestionnaire de secrets de l'hébergeur ; jamais dans GitHub public, les journaux ou les prompts.
4. Déployer d'abord un environnement de test avec données fictives.
5. Vérifier RLS, rôles minimaux, sauvegardes, restauration, rotation des secrets et alertes.
6. Tester les scénarios de reprise, idempotence, expiration de bail, arrêt d'urgence et restauration.
7. Garder communication externe, opérations financières et actes juridiques désactivés par défaut.
8. Obtenir une approbation explicite distincte avant tout service payant, hébergement payant, compte prestataire, intégration sensible ou activation de production.

## Contrôles locaux
`PYTHONPATH=runtime python -m papi_core security-check`

## Non réalisé
Aucun hébergement n'est créé, aucune migration distante n'est exécutée, aucun secret n'est configuré, aucun fournisseur de paiement n'est connecté et aucun agent n'est actif. Le contrôle local ne remplace pas un audit de sécurité indépendant, un test d'intrusion, la revue des politiques des prestataires ou une validation juridique.


## Revue complémentaire du 12 novembre 2026

Revue statique du dépôt effectuée sur les permissions Supabase, l'identité Ed25519, l'anti-rejeu, la mémoire locale, le planificateur et le worker.

### Constats vérifiés dans le code
- Les tables et fonctions RPC sensibles sont protégées par RLS, révocations de droits publics et permissions accordées à `service_role`.
- La consommation du nonce partagé utilise une insertion SQL atomique avec contrainte unique ; la vérification cryptographique précède sa consommation.
- Le registre Ed25519 local gère la version de clé, la rotation et la révocation ; les clés privées sont conservées localement avec des permissions restrictives.
- La mémoire locale refuse plusieurs motifs de secrets et champs sensibles, conserve un journal append-only et applique des règles de portée.
- Le planificateur calcule les échéances et retourne un statut de revue ; il n'enfile ni n'exécute les tâches.
- Le worker vérifie la politique avant réservation, exige une identité signée et ne termine un job qu'avec le bail correspondant.

### Points à traiter avant production
- Exécuter les tests d'intégration sur un projet Supabase de test et vérifier les droits effectifs avec les rôles réels.
- Compléter les tests de concurrence, expiration de bail, crash après effet métier et reprise idempotente.
- Renforcer la validation du schéma des événements mémoire et les contrôles d'autorisation des opérations de correction/archivage.
- Effectuer une revue indépendante de sécurité et un test d'intrusion.
- Ne pas activer le worker, les communications externes ni les opérations financières tant que ces validations ne sont pas terminées.

### Limite de cette revue
Cette revue est statique et fondée sur les fichiers du dépôt. Aucun test n'a été exécuté dans un environnement de déploiement, aucune connexion Supabase n'a été effectuée et aucun agent n'a été activé. Elle ne constitue pas une certification de sécurité.
