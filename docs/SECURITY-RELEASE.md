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
