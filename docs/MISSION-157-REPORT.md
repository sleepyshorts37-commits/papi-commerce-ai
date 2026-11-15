# Mission 157 — Modèles de planification systemd

## Livrable
- Service one-shot quotidien de sauvegarde à 02:00 UTC.
- Service one-shot de copie et vérification hors site à 03:00 UTC.
- Timers systemd avec rattrapage après indisponibilité (\`Persistent=true\`) et décalage aléatoire.
- Services exécutés via Docker Compose, avec restrictions systemd additionnelles et UMask 0077.
- Les deux timers ont une section \`[Install]\` mais ne sont ni installés ni activés par ce dépôt.
- Tests statiques des horaires, profils et absence d'activation par défaut.

## Mise en service manuelle
L'opérateur doit adapter le chemin \`/opt/papi-kids/infra/papi-kids\`, copier les unités dans \`/etc/systemd/system\`, exécuter \`systemctl daemon-reload\`, tester les commandes manuelles, puis activer explicitement les timers. L'activation de sauvegardes automatiques n'est pas effectuée ici.
