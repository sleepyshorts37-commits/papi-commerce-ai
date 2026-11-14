# Mission 41 — Prompt détaillé

Implémenter un registre local durable et transactionnel de reçus pour les paquets référentiels, en réutilisant les missions 39–40.

Exigences : vérifier Ed25519, propriétaire, scope, TTL, digest et destination avant inscription; ne conserver que métadonnées et références; garantir l'atomicité SQLite du reçu et de ses lignes; rendre idempotent un digest identique après nouvelle approbation; rejeter collisions d'événements/ressources sans écriture partielle; n'importer, transporter ou exécuter aucun contenu; ajouter tests adversariaux et documentation; valider CI sur le SHA final et laisser la PR ouverte, brouillon, non fusionnée.

Interdictions : aucun secret dans Git, aucune connexion Supabase hébergée, migration distante, déploiement, message externe, publication, paiement ou dépense.
