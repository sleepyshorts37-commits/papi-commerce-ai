# Mission 37 — Procédure opérateur PAPI CHAT

1. Conserver les journaux réels hors du dépôt public et ne pas y placer de données personnelles/confidentielles.
2. Sauvegarder le fichier JSONL avant toute maintenance.
3. Si une ligne est invalide, arrêter la lecture et préserver une copie forensique avant correction.
4. Ne pas supprimer automatiquement les doublons ou les lignes vides : toute réparation doit être contrôlée et tracée.
5. Après restauration, exécuter les tests PAPI CHAT et vérifier l'unicité des identifiants.
6. Le journal demeure local et mono-instance ; aucune garantie de verrouillage multi-processus, de chiffrement ou de synchronisation distante n'est fournie.
7. Aucun message n'est envoyé sur Internet par ces fonctions.
