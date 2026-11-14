# Clôture — Mission 21 : mémoire partagée et PAPI CHAT

## Livrables
1. Migration SQL append-only et RLS restrictive pour mémoire et messages.
2. Adaptateurs backend injectables avec principal d'agent authentifié.
3. Pagination keyset et idempotence des écritures.
4. Aperçu de réconciliation local/distant sans écriture, avec détection des conflits.
5. Rapport de préparation vérifiant le contrat et listant les blocages avant synchronisation.

## État réel
- Fondations de persistance et adaptateurs : codés.
- Tests unitaires et validation SQL sur PostgreSQL jetable : soumis à CI.
- Synchronisation sur un projet Supabase hébergé : non réalisée.
- Tests réels inter-instances : non réalisés.
- Transfert de journaux historiques : non réalisé.
- Synchronisation automatique, workers permanents et scheduler : désactivés.
- Merge et déploiement : non autorisés et non effectués.

## Conditions restantes avant activation
- Projet Supabase de test choisi et autorisé.
- Vérification indépendante des politiques RLS, permissions et secrets.
- Tests d'intégration inter-instances reproductibles.
- Procédure d'approbation humaine des différences et transferts.
- Procédure de sauvegarde, restauration et arrêt.

La Mission 21 termine les fondations techniques et les garde-fous de préparation. Elle ne doit pas être présentée comme une synchronisation déjà opérationnelle.
