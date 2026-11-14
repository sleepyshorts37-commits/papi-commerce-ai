# Mission 49 — Migration contrôlée JSONL vers SQLite

Créer une procédure logicielle sûre et vérifiable pour migrer les anciens journaux JSONL mémoire et PAPI CHAT vers le magasin SQLite local introduit en Mission 48.

Exigences : validation avant écriture, sauvegarde sans écrasement, SHA-256 de la source et de la sauvegarde, transaction atomique, unicité, détection des collisions, idempotence, source préservée, limite de taille, CLI locale, tests de rollback et documentation opératoire.

Garde-fous : ne jamais supprimer/modifier les JSONL, ne pas lancer la migration sur des données de production, aucun accès distant, aucune activation de worker/scheduler, aucune publication, communication externe ou action financière.
