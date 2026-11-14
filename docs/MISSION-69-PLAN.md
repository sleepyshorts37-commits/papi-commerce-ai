# Mission 69 — Contrat sémantique des snapshots d'identité

## Ordre unique d'exécution — 20 journées

Exécuter cet ordre en continu selon la méthode de Mission 65 : une seule branche, un seul ordre de vingt journées et une seule PR brouillon. Ne pas fusionner ni déployer.

## Objectif
Ajouter une couche de validation sémantique commune après l'extraction sécurisée JSON/SQLite. Elle doit détecter les identifiants ambigus, doublons, statuts invalides, capacités mal formées ou contradictoires, ainsi que les versions transactionnelles invalides, avant le rapprochement. Les validations sont passives et ne modifient jamais les sources.

## Vingt journées de travail
1. Cartographier les structures réellement émises par le registre canonique et l'adaptateur SQLite.
2. Définir les invariants communs sans imposer une liste fermée de statuts métier.
3. Définir une grammaire bornée et stable pour les identifiants d'agents.
4. Définir les limites de longueur des statuts et capacités.
5. Refuser les entrées qui ne sont pas des objets.
6. Refuser les identifiants absents, mal formés et dupliqués.
7. Valider les statuts comme chaînes non vides et bornées.
8. Valider les permissions comme listes de chaînes non vides.
9. Valider les interdictions avec les mêmes contraintes.
10. Refuser les capacités dupliquées dans chaque liste.
11. Refuser toute capacité présente simultanément dans permissions et prohibited.
12. Limiter le nombre de capacités par identité.
13. Valider strictement revision et key_version comme entiers positifs non booléens.
14. Créer un module contractuel indépendant des E/S.
15. Brancher les validateurs après extraction et avant rapprochement.
16. Ajouter les tests unitaires des invariants et cas limites.
17. Vérifier que les validations ne normalisent ni ne mutent les snapshots.
18. Documenter les invariants, limites et compatibilité avec le registre courant.
19. Exécuter la CI GitHub et corriger les défauts révélés.
20. Mettre à jour roadmap et rapport, vérifier le SHA exact et ouvrir une PR brouillon unique.

## Livrables
- runtime/papi_core/identity_snapshot_contract.py
- runtime/papi_core/identity_snapshot.py (intégration)
- tests/test_identity_snapshot_contract.py
- docs/MISSION-69-PLAN.md
- docs/MISSION-69-REPORT.md
- docs/ROADMAP.md

## Critères d'acceptation
- Identifiants valides, uniques et bornés.
- Statuts non vides et bornés, sans liste fermée arbitraire.
- Permissions/interdictions constituées de chaînes uniques, bornées et disjointes.
- Révision et version de clé entières strictement positives.
- Validation exécutée avant le moteur de rapprochement.
- Tests couvrant doublons, valeurs invalides, contradictions et limites.
- CI verte sur le SHA exact de tête pour clôturer la mission.

## Gouvernance
Lecture seule. Aucun accès réseau applicatif, secret, mutation de registre/ledger, activation, révocation, changement de permission, création de clé, transaction financière, publication, prospection, fusion ou déploiement.
