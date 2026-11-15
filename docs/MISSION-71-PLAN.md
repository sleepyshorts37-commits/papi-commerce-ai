# Mission 71 — Ingestion stricte des rapports de rapprochement

## Ordre unique d'exécution — 20 journées

1. Cartographier les frontières d'entrée des rapports et les usages existants.
2. Définir un format JSON UTF-8 portable pour l'échange des rapports.
3. Définir une limite maximale de taille en octets.
4. Refuser les entrées qui ne sont pas des octets.
5. Refuser les documents dépassant la limite avant décodage.
6. Décoder UTF-8 en mode strict, sans remplacement silencieux.
7. Refuser les clés JSON dupliquées à tous les niveaux.
8. Refuser NaN et les constantes numériques infinies non standard.
9. Refuser les documents JSON mal formés et les récursions excessives.
10. Exiger un objet JSON racine.
11. Réutiliser le contrat strict de la Mission 70 après parsing.
12. Traduire les erreurs de contrat en erreur d'ingestion stable.
13. Ajouter une sérialisation canonique des rapports validés.
14. Garantir que la canonicalisation ne modifie pas l'objet fourni.
15. Tester l'aller-retour rapport valide → JSON → rapport.
16. Tester les clés dupliquées, UTF-8 invalide et JSON non standard.
17. Tester la limite de taille et les types de racine incorrects.
18. Tester le rejet des rapports au digest ou schéma invalides.
19. Documenter la limite : validation locale, aucune preuve d'origine ni stockage.
20. Mettre à jour roadmap/rapport, exécuter la CI et vérifier le SHA exact avant PR brouillon.

## Livrables
- runtime/papi_core/identity_reconciliation_artifact.py
- tests/test_identity_reconciliation_artifact.py
- docs/MISSION-71-PLAN.md
- docs/MISSION-71-REPORT.md
- docs/ROADMAP.md

## Critères d'acceptation
- Parsing UTF-8 strict et taille bornée avant décodage.
- Clés dupliquées et constantes numériques non standard rejetées.
- Contrat Mission 70 exécuté pour tout rapport ingéré.
- Sérialisation canonique stable, sans mutation de l'objet source.
- Tests positifs et négatifs reproductibles.
- CI verte sur le SHA exact de tête.

## Gouvernance
Traitement local en mémoire uniquement. Aucun accès fichier, réseau, base de données, écriture de registre, activation d'agent, transaction commerciale, publication, fusion ou déploiement.
