# Mission 46 — Exploitation et garde-fous

- Travailler sur une copie locale de la base de reçus/imports et conserver les deux fichiers sources.
- Vérifier l'identifiant exact de l'instance destinataire avant la commande.
- Utiliser le registre public de clés approuvé et le registre d'agents courant ; la clé privée ne doit jamais être copiée dans le dépôt.
- Une commande échouée doit laisser nonce, reçu et contenus inchangés grâce au rollback SQLite.
- Une réponse `already_imported` indique une répétition idempotente ; ne pas interpréter cela comme un nouveau transfert.
- Ne pas exposer le contenu importé dans les logs ; limiter les permissions du répertoire et de la base.
- Ne pas activer les agents, le réseau, le scheduler ou les workers à la suite de l'import.
- Prévoir une sauvegarde cohérente de la base SQLite avant les opérations réelles. Cette mission ne fournit pas de sauvegarde distante.
