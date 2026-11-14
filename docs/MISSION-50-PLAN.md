# Mission 50 — Plan

- [x] Examiner le magasin SQLite et la migration existante.
- [x] Concevoir le snapshot cohérent via sqlite3.Connection.backup.
- [x] Ajouter un manifeste versionné avec taille, SHA-256 et contrôles SQLite.
- [x] Refuser les liens symboliques et les chemins ambigus.
- [x] Implémenter une restauration atomique vers une destination absente.
- [x] Ajouter la CLI de sauvegarde, vérification et restauration.
- [x] Ajouter les tests de snapshot, restauration, corruption, collision et symlink.
- [x] Documenter les commandes et les limites.
- [ ] Vérifier les tests complets et l'intégration CI sur le SHA final.