# Mission 158 — Preuve de copie hors site et inventaire santé

## Livrable
- Après copie et \`rclone check --one-way --checksum\` réussis, écrit atomiquement un rapport privé \`offsite-verification.json\`.
- Preuve par fichier liée au nom, SHA-256 chiffré, remote alias et horodatage UTC.
- Le rapport reste séparé des manifestes de sauvegarde et n'est pas inclus dans les filtres de transfert.
- \`load_backup_health_inventory\` vérifie à nouveau le SHA-256 local et recalcule la référence de preuve avant de marquer la copie hors site comme vérifiée.
- Les preuves absentes, altérées ou non correspondantes ne rendent jamais une sauvegarde saine.
- Tests de création de preuve, permissions 0600 et rejet d'une preuve non liée.

## Limites
La preuve locale constate le succès de rclone et du contrôle checksum ; elle ne remplace pas un audit indépendant du fournisseur distant. Aucun transfert réel n'a été effectué.
