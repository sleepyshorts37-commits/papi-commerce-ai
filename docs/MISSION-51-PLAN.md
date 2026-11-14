# Mission 51 — Plan

- [x] Auditer les snapshots SQLite de la Mission 50 et la dépendance cryptographique déjà présente.
- [x] Ajouter génération locale exclusive de clés AES-256.
- [x] Ajouter chiffrement authentifié AES-256-GCM avec nonce et AAD.
- [x] Ajouter vérification ciphertext, authentification et intégrité SQLite.
- [x] Ajouter déchiffrement vers un nouveau chemin sans écrasement.
- [x] Ajouter ré-encryptage avec une nouvelle clé sans supprimer l'original.
- [x] Ajouter tests adversariaux : clé incorrecte, altération, collisions, permissions et rotation.
- [x] Documenter les commandes et le cycle de vie des clés.
- [ ] Vérifier CI sur le SHA final et corriger tout défaut détecté.