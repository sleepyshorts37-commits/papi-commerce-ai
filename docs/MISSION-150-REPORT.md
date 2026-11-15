# Mission 150 — Sondes de disponibilité production

## Livrable
- \`GET /healthz\` reste une sonde liveness simple et indépendante des dépendances.
- Nouveau \`GET /readyz\` vérifie une requête PostgreSQL réelle (\`SELECT 1\`) et les permissions du volume privé (répertoire, non-symlink, mode 0700, accès écriture/exécution).
- Retourne 200 uniquement si les deux composants sont prêts ; 503 sinon.
- Réponse limitée à des booléens de composants, sans URL, secret, erreur SQL ni chemin privé.
- Ferme curseur et connexion même en cas d'échec.
- Tests hors réseau pour disponibilité complète et panne PostgreSQL.

## Opérations
Le reverse proxy/orchestrateur peut utiliser \`/readyz\` pour le routage de trafic. \`/healthz\` reste utile pour détecter si le processus HTTP répond. La sonde Docker actuelle reste liveness et n'est pas modifiée.
