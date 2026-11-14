# Mission 67 — Adaptateurs de snapshots d'identité en lecture seule

## Ordre unique d'exécution — 20 journées regroupées

Exécuter cet ordre en continu, selon la méthode de Mission 65 : un seul ordre de travail couvrant vingt journées, une branche unique, une PR brouillon unique. Ne pas solliciter de validation intermédiaire pour les modifications internes, tests et documentation. Ne jamais fusionner ni déployer.

## Objectif
Faire évoluer le rapprochement de Mission 66 d'un moteur recevant des instantanés préparés manuellement vers une chaîne locale d'extraction strictement en lecture seule : registre canonique JSON et ledger SQLite transactionnel. Produire un instantané validé, traçable, puis un rapport de rapprochement déterministe. Aucun accès réseau, aucune mutation, aucun démarrage/initialisation de base, aucune activation d'agent.

## Vingt journées de travail
1. Auditer les contrats du registre canonique et du ledger SQLite.
2. Définir le contrat d'extraction et les limites de confiance.
3. Définir les contrôles de chemins, types de fichiers et tailles.
4. Implémenter le chargement JSON en UTF-8 strict, sans suivre les liens symboliques.
5. Valider le schéma racine et la collection agents.
6. Implémenter l'ouverture SQLite en mode URI read-only.
7. Interdire toute création automatique de base ou de schéma.
8. Vérifier les tables et colonnes attendues avant lecture.
9. Extraire les états d'identité avec ordre déterministe.
10. Ajouter les métadonnées minimales de provenance sans exposer de données sensibles.
11. Relier les snapshots à l'algorithme de rapprochement Mission 66.
12. Définir les erreurs fail-closed pour sources absentes, corrompues ou incompatibles.
13. Tester les chemins symboliques et fichiers non réguliers.
14. Tester les bases absentes, schémas incomplets et accès lecture seule.
15. Tester l'absence de mutation des fichiers et de la base.
16. Tester l'intégration complète avec des données temporaires.
17. Documenter l'usage local, les prérequis et les limites.
18. Auditer les permissions et les garanties d'absence d'écriture.
19. Exécuter la suite CI, corriger les défauts observés et contrôler le SHA final.
20. Mettre à jour roadmap, rapport, ouvrir une PR brouillon unique.

## Livrables
- runtime/papi_core/identity_snapshot.py
- tests/test_identity_snapshot.py
- docs/MISSION-67-PLAN.md
- docs/MISSION-67-REPORT.md
- mise à jour docs/ROADMAP.md

## Critères d'acceptation
- JSON chargé sans tolérance aux encodages ou structures invalides.
- SQLite ouvert exclusivement en mode lecture seule, sans création de fichier.
- Vérification des tables/colonnes avant extraction.
- Résultats déterministes et raccordés au rapprochement de Mission 66.
- Sources invalides ou ambiguës : erreur explicite, aucun repli permissif.
- Tests prouvant l'absence de mutation.
- CI verte sur le SHA exact de tête pour clôturer la mission.

## Gouvernance
Aucun accès distant, secret, connexion Supabase, migration, écriture de base, activation/révocation, changement de permission, création de clé, worker, scheduler, publication, prospection, transaction financière, fusion ou déploiement. Le composant est local, passif et strictement read-only.
