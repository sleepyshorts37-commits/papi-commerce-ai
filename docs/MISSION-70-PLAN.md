# Mission 70 — Contrat d'intégrité des rapports de rapprochement

## Ordre unique d'exécution — 20 journées

1. Cartographier le rapport réellement émis par le moteur de rapprochement.
2. Définir le schéma versionné du rapport et ses invariants.
3. Définir les types stricts des compteurs et indicateurs booléens.
4. Définir les champs obligatoires des écarts et les sévérités admises.
5. Vérifier l'unicité des couples identité/code d'écart.
6. Vérifier l'ordre déterministe des écarts.
7. Vérifier la cohérence entre compteurs et contenu.
8. Vérifier la cohérence de l'indicateur consistent.
9. Vérifier la règle fail_closed sur les écarts critiques.
10. Définir la sérialisation canonique indépendante des entrées.
11. Vérifier le format du digest SHA-256.
12. Recalculer le digest en excluant uniquement report_sha256.
13. Créer un module de contrat indépendant des E/S.
14. Intégrer la vérification au moteur avant retour du rapport.
15. Ajouter tests de rapport valide et de déterminisme.
16. Ajouter tests de champs absents, types incorrects et compteurs incohérents.
17. Ajouter tests de sévérité, doublons, ordre et booléens.
18. Ajouter tests de digest falsifié et de modification après signature.
19. Documenter les limites : intégrité interne, pas preuve d'origine ni signature du propriétaire.
20. Mettre à jour roadmap/rapport, exécuter la CI, vérifier le SHA exact et créer une PR brouillon unique.

## Livrables
- runtime/papi_core/identity_reconciliation_contract.py
- runtime/papi_core/identity_reconciliation.py (validation avant retour)
- tests/test_identity_reconciliation_contract.py
- docs/MISSION-70-PLAN.md
- docs/MISSION-70-REPORT.md
- docs/ROADMAP.md

## Critères d'acceptation
- Schéma de rapport versionné et strictement typé.
- Champs d'écart validés, sévérités limitées à critical/high.
- Compteurs, consistent et fail_closed cohérents avec les écarts.
- Ordre des écarts déterministe et couples identité/code uniques.
- Digest SHA-256 recalculé sur le rapport canonique sans le champ digest.
- Tests positifs et négatifs couvrant les invariants.
- CI verte sur le SHA exact de tête.

## Gouvernance
Contrôle local et en lecture seule. Aucun changement des registres, ledger, permissions, clés ou états d'agents. Aucun réseau applicatif, secret, activation, transaction, publication, prospection, fusion ou déploiement.
