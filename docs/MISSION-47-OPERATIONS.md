# Mission 47 — Exploitation

- Passer explicitement le chemin de la base SQLite à `import_db`; aucun magasin n'est activé par défaut.
- Le lecteur SQLite est strictement en lecture seule et refuse les bases symboliques ou les schémas incomplets.
- Le reçu doit être présent, dans l'état attendu, et contenir la référence exacte de chaque ligne importée.
- Les empreintes sont recalculées à chaque lecture ; toute incohérence arrête la lecture.
- Les identifiants en collision entre JSONL local et SQLite importé provoquent un refus.
- Les appels mémoire doivent fournir un principal agent authentifié.
- Sauvegarder la base avant toute opération de maintenance ; cette mission n'ajoute aucune fonction d'écriture.
- Ne pas activer workers, transport, scheduler, publication, messagerie externe, paiements ou dépenses.
