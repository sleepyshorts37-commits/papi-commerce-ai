# Mission 48 — Procédure d'exploitation

1. Conserver une sauvegarde vérifiée des fichiers JSONL avant toute bascule.
2. Choisir un chemin SQLite local protégé, hors dépôt Git si des données réelles y seront stockées.
3. Configurer explicitement `sqlite_db` sur les opérations d'écriture et de lecture d'un même domaine.
4. Ne pas mélanger sans plan les écritures JSONL et SQLite pour une même instance. Les lecteurs détectent les collisions divergentes, mais ne réalisent pas de fusion automatique.
5. Vérifier les permissions du fichier (0600) et du dossier (0700), les sauvegardes et la restauration.
6. En cas d'erreur SQLite, arrêter l'écriture et préserver la base pour diagnostic ; ne pas contourner les contraintes append-only.
7. Ne pas connecter la base à un transport ou à un worker sans validation distincte.

Le mode SQLite reste local et facultatif. Aucun changement distant n'est effectué par cette mission.
