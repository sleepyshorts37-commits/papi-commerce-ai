# Mission 68 — Durcissement des entrées de snapshots d'identité

## Ordre unique d'exécution — 20 journées regroupées

Exécuter cet ordre en continu selon la méthode de Mission 65 : un seul ordre de travail de vingt journées, une seule branche et une seule PR brouillon. Effectuer les changements internes, tests et documentation sans validation intermédiaire. Ne jamais fusionner ni déployer.

## Objectif

Renforcer la frontière d'entrée créée en Mission 67. Les adaptateurs doivent lire les sources locales sans suivre de liens symboliques, limiter les ressources consommées, détecter les entrées JSON ambiguës, valider strictement les données SQLite et échouer de manière fermée. Le résultat reste une extraction locale et passive, sans correction des sources ni activation d'agents.

## Vingt journées de travail

1. Revoir les chemins de lecture et les risques de liens symboliques.
2. Définir les garanties de descripteur et les limites de portabilité.
3. Remplacer les ouvertures de fichiers par descripteurs O_NOFOLLOW lorsque disponible.
4. Vérifier le type régulier via fstat après ouverture.
5. Lire le registre JSON par blocs avec plafond strict de taille.
6. Détecter les modifications de taille ou métadonnées pendant la lecture.
7. Refuser les encodages UTF-8 invalides.
8. Refuser les clés JSON dupliquées et constantes numériques non finies.
9. Valider strictement la racine JSON et la collection d'agents.
10. Ouvrir le ledger via un descripteur préalablement contrôlé.
11. Utiliser exclusivement une URI SQLite en mode lecture seule.
12. Éviter le remplacement du chemin entre contrôle et ouverture SQLite en liant l'URI au descripteur sur les environnements compatibles.
13. Vérifier les tables et colonnes avant toute extraction.
14. Valider identifiants, statuts, révisions et versions de clés.
15. Valider les listes JSON de permissions et d'interdictions et leurs limites.
16. Ajouter des tests pour doublons JSON, NaN, fichiers volumineux, liens symboliques et valeurs SQLite invalides.
17. Tester l'absence de création ou de modification des sources.
18. Documenter les garanties, dépendances plateforme et limites résiduelles.
19. Exécuter la CI, examiner les jobs et corriger les défauts observés.
20. Mettre à jour roadmap et rapport, vérifier le SHA exact, ouvrir une PR brouillon unique.

## Livrables

- runtime/papi_core/identity_snapshot.py
- tests/test_identity_snapshot.py
- docs/MISSION-68-PLAN.md
- docs/MISSION-68-REPORT.md
- mise à jour docs/ROADMAP.md

## Critères d'acceptation

- Les fichiers symboliques et non réguliers sont refusés.
- Le JSON est lu via un descripteur contrôlé, en UTF-8 strict et sous plafond.
- Les clés dupliquées et nombres non finis sont refusés.
- SQLite est lu en mode ro à partir d'un descripteur déjà ouvert sur les environnements compatibles ; absence de /proc/self/fd entraîne un refus explicite.
- Les champs extraits sont validés avant de rejoindre le moteur de rapprochement.
- Les tests prouvent le refus des entrées malformées et l'absence de mutation.
- La CI doit être verte sur le SHA exact de tête pour clôturer la mission.

## Gouvernance et limites

Aucun accès réseau, secret, écriture ou migration de base, correction automatique, activation/révocation, changement de permission, création de clé, worker, scheduler, publication, prospection, transaction financière, fusion ou déploiement. L'adaptateur reste local et passif. Les garanties de descripteur SQLite dépendent de /proc/self/fd ; les plateformes sans ce mécanisme échouent volontairement en mode fermé.
