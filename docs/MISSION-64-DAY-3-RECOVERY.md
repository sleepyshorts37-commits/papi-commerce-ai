# Mission 64 — Jour 3 : intégration et reprise

La rotation utilise désormais l'ordre journal durable → clé privée → registre public → suppression durable du journal. La récupération est exécutée avant une nouvelle rotation et avant toute signature locale.

- Ancien registre + ancienne clé : transaction non commencée ; le journal peut être supprimé.
- Ancien registre + nouvelle clé : rollback de la clé privée vers l'ancien état.
- Nouveau registre + nouvelle clé : commit confirmé ; le journal peut être supprimé.
- Toute autre combinaison : refus fermé et conservation du journal.

La fonction de signature accepte un chemin de registre explicite optionnel, sans casser les appels existants.
