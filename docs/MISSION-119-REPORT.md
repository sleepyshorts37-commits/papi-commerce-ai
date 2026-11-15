# Mission 119 — Prévisualisation sûre de synchronisation mémoire et messagerie

## Objectif (bloc de cinq jours)
Préparer la synchronisation entre instances PAPI en réunissant les snapshots locaux et distants de mémoire partagée et PAPI CHAT, sans autoriser de transfert automatique ni de résolution implicite des conflits.

## Constat initial
- Les modules locaux mémoire et messagerie fonctionnent sur des journaux JSONL indépendants.
- Les tables Supabase de collaboration, les contraintes d'idempotence et l'adaptateur SharedCollaborationStore existent déjà.
- build_reconciliation_preview compare deux snapshots explicites et build_sync_readiness_report impose un mode strictement sans écriture.
- Il manquait un orchestrateur qui lise toutes les pages distantes, détecte les boucles, doublons et snapshots tronqués, puis fournisse un rapport unique de préparation.

## Plan des cinq jours
1. Définir le contrat de snapshot distant paginé et les limites de volume.
2. Implémenter l'orchestrateur en lecture seule sur adaptateur explicitement injecté.
3. Refuser les curseurs répétés, identifiants répétés, payloads mal formés et snapshots incomplets.
4. Raccorder la réconciliation et le rapport de readiness sans aucune écriture.
5. Ajouter tests de pagination/échec fermé, documentation et CI.

## Livrables
- runtime/papi_core/collaboration_sync.py : collecte paginée des mémoires et messages distants, avec plafonds explicites et échec fermé.
- tests/test_collaboration_sync.py : pagination complète, rejeu de curseur, doublon inter-pages, plafond atteint, payload invalide et absence d'adaptateur.
- Ce rapport de mission.

## Garanties
- Aucune méthode d'écriture de l'adaptateur n'est appelée.
- Aucun transfert, suppression, modification, résolution de conflit ou approbation n'est exécuté.
- La pagination est bornée à 100 pages par domaine et 100 éléments par page.
- Un snapshot incomplet ne peut pas être présenté comme complet.
- Les filtres d'accès et de portée restent appliqués par SharedCollaborationStore et la réconciliation.
- L'accès réseau n'existe que si un adaptateur serveur est explicitement fourni par l'appelant.

## Limites
- Aucun projet Supabase hébergé n'a été contacté.
- Aucun transfert réel entre instances n'est activé.
- La revue indépendante de sécurité et les tests sur un projet Supabase de test restent des portes obligatoires avant production.
- Les conflits et différences exigent une décision humaine avant toute synchronisation.

## Validation
À compléter après exécution des tests unitaires et des workflows GitHub Actions sur la branche dédiée. Aucun merge vers main.
