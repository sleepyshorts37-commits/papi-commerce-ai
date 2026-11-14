# Mission 52 — Manifeste de sauvegarde chiffrée authentifié

## Objectif
Renforcer l'intégrité cryptographique des métadonnées des sauvegardes SQLite chiffrées, sans changer les rôles des agents ni activer de service externe.

## Périmètre de cinq jours
1. Auditer le manifeste AES-GCM de la Mission 51 et identifier les champs non couverts par l'AAD.
2. Introduire un format v2 liant cryptographiquement les métadonnées critiques.
3. Valider strictement schéma, types, tailles, nonce, horodatage et nom du fichier chiffré.
4. Préserver la lecture des manifestes v1 existants.
5. Ajouter tests de falsification, compatibilité, documentation et rapport.

## Critères d'acceptation
- Les nouvelles sauvegardes utilisent v2.
- La modification d'un champ authentifié est rejetée.
- Les manifestes malformés, champs inattendus et tailles invalides sont rejetés.
- Les manifestes v1 valides restent lisibles.
- Aucun secret ni aucune donnée réelle ne sont ajoutés au dépôt.
- CI final réussi sur le SHA de tête exact ; PR ouverte en brouillon et non fusionnée.

## Hors périmètre
Aucun stockage distant de clés, HSM/KMS, déploiement, migration distante, worker, scheduler, contact externe, publication ou paiement.
