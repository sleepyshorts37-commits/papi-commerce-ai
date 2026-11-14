# Mission 51 — Chiffrement et gestion sécurisée des clés

Ajouter le chiffrement authentifié des sauvegardes SQLite locales, la création locale de clés, la vérification avant restauration et une procédure de rotation. Utiliser AES-256-GCM, nonce aléatoire, AAD, manifeste vérifiable, permissions restrictives et refus des collisions/symlinks. Les clés ne doivent jamais être écrites dans Git, logs, PR ou manifestes.

Aucune clé ne sera créée dans l'environnement du dépôt et aucune donnée réelle ne sera traitée. Aucun secret GitHub, service cloud, déploiement, worker, scheduler ou action externe ne sera utilisé.