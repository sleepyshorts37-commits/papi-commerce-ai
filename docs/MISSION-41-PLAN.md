# Mission 41 — Plan de travail sur cinq jours

1. Jour 1 — Audit : vérifier contrats de paquet, validation Ed25519 et anti-rejeu; établir le modèle du reçu.
2. Jour 2 — Registre : créer schéma SQLite minimal, contraintes d'unicité et permissions restrictives.
3. Jour 3 — Transaction : implémenter vérification préalable, insertion atomique, idempotence et rejet des collisions.
4. Jour 4 — Tests adversariaux : paquet valide, rejeu, mauvaise destination, altération, digest répété, conflit événement/ressource et absence d'écriture partielle.
5. Jour 5 — Livraison : documenter limites/reprise, actualiser roadmap, exécuter tests et CI sur le SHA final, ouvrir une PR brouillon.

Sortie attendue : registre local de reçus vérifiables; aucun import ou transport activé.
