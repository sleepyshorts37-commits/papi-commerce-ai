# Mission 50 — Sauvegarde et restauration SQLite

Développer des outils locaux de sauvegarde cohérente, vérification cryptographique d'intégrité par SHA-256 et restauration contrôlée pour les bases SQLite locales de PAPI COMMERCE AI.

Exigences : API SQLite backup, manifeste versionné, contrôle PRAGMA integrity_check, taille et SHA-256, permissions restrictives, refus des liens symboliques, restauration vers une destination neuve uniquement, aucune écrasement, tests de corruption et documentation CLI.

Garde-fous : aucun accès aux données réelles de l'utilisateur, aucune sauvegarde distante, aucun déploiement, worker, scheduler, publication, contact externe ou action financière.