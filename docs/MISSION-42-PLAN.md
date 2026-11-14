# Mission 42 — Plan de travail sur cinq jours

1. Jour 1 — Auditer la séquence de validation Ed25519 et le registre Mission 41; formaliser la fenêtre de panne.
2. Jour 2 — Ajouter une vérification cryptographique sans consommation anticipée du nonce, sans changer le comportement par défaut des autres appels.
3. Jour 3 — Implémenter la transaction SQLite unique : nonce, reçu et références.
4. Jour 4 — Tester rejeu, idempotence, mauvaise destination, collisions, rollback intégral et absence d'import.
5. Jour 5 — Documenter, actualiser la roadmap, lancer la suite et CI sur le SHA final; ouvrir une PR brouillon.

Résultat attendu : atomicité locale nonce + reçu; aucun transport ou import métier.
