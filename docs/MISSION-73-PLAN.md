# Mission 73 — PAPI KIDS PUBLISHING : fondations opérationnelles (20 jours)

## Priorité stratégique
PAPI KIDS PUBLISHING est le premier département à préparer pour le lancement de PAPI COMMERCE AI. Les autres divisions ne doivent pas détourner les ressources de ce chantier tant que le pilote livres n'a pas franchi ses contrôles.

## Objectif
Passer d'une division uniquement documentée (24 postes planifiés) à un socle local testable pour gérer les livres, leurs fichiers, les contrôles éditoriaux, les droits, la conformité KDP et l'approbation humaine.

## Programme de travail
1. Auditer les 24 rôles, les trois activités et le workflow éditorial-commercial.
2. Corriger les anomalies de documentation et relier la division au README et à la roadmap.
3. Définir le contrat versionné du catalogue livres.
4. Initialiser un catalogue vide et strictement validable.
5. Définir les identifiants et statuts de projets de livres.
6. Ajouter le contrôle des doublons et des champs obligatoires.
7. Ajouter les contrôles de tranche d'âge et de format.
8. Définir les pièces attendues pour broché et numérique.
9. Ajouter la vérification locale des chemins, liens symboliques et tailles.
10. Ajouter le calcul SHA-256 des pièces de production.
11. Définir les portes de contrôle droits, qualité et conformité KDP.
12. Imposer une approbation humaine distincte des contrôles techniques.
13. Ajouter une commande de validation du catalogue.
14. Ajouter un rapport local du portefeuille de livres.
15. Ajouter un contrôle de préparation d'un livre donné.
16. Couvrir les scénarios négatifs par tests unitaires.
17. Vérifier qu'aucune action externe n'est déclenchée.
18. Documenter les limites et les contrôles non encore réalisés.
19. Actualiser la roadmap et les critères du pilote de cinq livres.
20. Ouvrir une PR brouillon et vérifier la CI sur le SHA exact.

## Critères d'acceptation
- 24 rôles conservés comme postes planifiés, sans prétendre qu'ils sont activés.
- Catalogue JSON versionné, strict, sans clés dupliquées ni constantes non standard.
- Vérification des fichiers par chemin contrôlé et SHA-256.
- Portes indépendantes pour droits, qualité, conformité KDP et validation humaine.
- Aucun code de soumission/publication, réseau, dépense, compte externe, worker permanent ou scheduler.
- Tests CI verts sur le SHA exact avant de qualifier la mission de validée.

## Limites
Le statut « prêt pour revue humaine » ne signifie ni éligibilité KDP confirmée, ni publication, ni vente. Les conditions Amazon KDP et les moyens de versement depuis le Sénégal devront être vérifiés séparément avant le pilote.
