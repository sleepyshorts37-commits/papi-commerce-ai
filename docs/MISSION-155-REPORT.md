# Mission 155 — Runner Docker de sauvegarde chiffrée

## Livrable
- Image dédiée \`Backup.Dockerfile\` avec PostgreSQL client et exécution non-root.
- Service Compose \`papi-kids-backup\` activable uniquement via le profil \`backup\`.
- Volume chiffré persistant distinct du volume des manuscrits.
- Runner one-shot, désactivé par défaut via \`PAPI_KIDS_BACKUP_ENABLED=false\`.
- Vérifie le volume privé en mode 0700, le dossier, le secret et l'identifiant de clé avant d'appeler le job de sauvegarde.
- N'affiche que le nom des fichiers et le statut, jamais l'URL DB ni les secrets.
- Tests offline pour le verrou désactivé, les permissions et l'activation explicite.

## Utilisation contrôlée
1. Configurer les secrets serveur et le volume de sauvegarde.
2. Construire l'image dédiée.
3. Activer explicitement \`PAPI_KIDS_BACKUP_ENABLED=true\` dans le fichier serveur non versionné.
4. Lancer manuellement \`docker compose --profile backup run --rm papi-kids-backup\`.
5. Vérifier le manifeste, puis transférer la sauvegarde chiffrée vers un stockage hors site.

Aucun cron ni déclenchement automatique n'est activé.
