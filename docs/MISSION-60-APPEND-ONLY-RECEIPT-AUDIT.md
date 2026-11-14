# Mission 60 — Registre de reçus append-only et audit d'intégrité

## Objectif
Renforcer la conservation locale des reçus de transport signés et permettre de détecter les altérations accidentelles ou non autorisées du journal.

## Implémentation
- Ajout de déclencheurs SQLite qui refusent toute mise à jour ou suppression d'un reçu existant.
- Conservation du modèle d'insertion uniquement, avec les contraintes d'unicité existantes sur receipt_id, delivery_id et receipt_sha256.
- Ajout d'un audit local en lecture seule qui recalcule SHA-256, contrôle l'encodage JSON canonique et vérifie la correspondance receipt_id / delivery_id entre colonnes et enveloppe.
- L'audit indique explicitement qu'il ne re-vérifie pas la signature cryptographique : il contrôle l'intégrité des données archivées et leur cohérence structurelle.
- Tests couvrant le refus UPDATE/DELETE et la détection d'une altération du JSON après neutralisation volontaire du trigger dans un scénario de test.

## Limites
Les triggers protègent contre les modifications SQL ordinaires, mais un acteur ayant le contrôle du fichier SQLite peut les supprimer ou réécrire le fichier. Ce journal local n'est donc pas un stockage inviolable ni une preuve externe d'horodatage. Une sauvegarde protégée et une revue indépendante restent nécessaires.

Aucun réseau, import, déploiement, worker, scheduler ou action externe n'est ajouté.
