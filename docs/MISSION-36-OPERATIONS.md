# Mission 36 — Procédure opérateur

1. Conserver le journal mémoire réel hors du dépôt public.
2. Sauvegarder le fichier JSONL avant toute opération de maintenance.
3. Ne jamais corriger manuellement une ligne corrompue sans conserver une copie forensique locale et faire valider la correction.
4. En cas d'échec de validation, arrêter les opérations de lecture/archivage et examiner la ligne signalée.
5. Après restauration depuis une sauvegarde, exécuter les tests mémoire et vérifier les IDs et références d'archivage.
6. Ne pas interpréter ces contrôles locaux comme une garantie de concurrence multi-processus ou de réplication distante.

Le journal reste local et mono-instance ; aucune synchronisation distante ni activation worker n'est introduite.
