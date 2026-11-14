# Mission 50 — Procédure opératoire

1. Choisir un dossier de sauvegarde protégé, distinct des bases actives.
2. Exécuter `sqlite-backup` sur la base locale.
3. Exécuter `sqlite-backup-verify` sur le manifeste généré.
4. Copier sauvegarde et manifeste vers un support distinct via une procédure approuvée.
5. Pour un test de reprise, restaurer vers un chemin neuf avec `sqlite-restore`.
6. Vérifier les données restaurées et les journaux attendus avant toute décision de bascule.
7. Ne jamais supprimer la base active ni écraser une destination existante sur la seule base du succès de la restauration.

La restauration fournie n'active pas automatiquement la base restaurée. Les chemins actifs et les bascules restent des décisions manuelles explicites.