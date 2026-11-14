# Mission 49 — Procédure opératoire

1. Arrêter les écrivains locaux du journal concerné.
2. Vérifier le chemin du JSONL, l'absence de lien symbolique et la disponibilité du stockage de sauvegarde.
3. Lancer la commande `migrate-jsonl` avec le bon `--kind`.
4. Contrôler `status`, `record_count`, `source_sha256` et `backup_path`.
5. Vérifier indépendamment le SHA-256 du fichier de sauvegarde et comparer les comptes source/cible.
6. Rejouer la commande pour vérifier le statut `already_migrated`.
7. Ne configurer `sqlite_db` dans l'application qu'après revue et approbation explicite.
8. Garder les sources JSONL et sauvegardes jusqu'à validation d'une procédure de restauration testée.

En cas d'échec, la source reste intacte et la transaction SQLite est annulée. La sauvegarde est conservée pour diagnostic. Ne pas contourner un conflit d'identité.
