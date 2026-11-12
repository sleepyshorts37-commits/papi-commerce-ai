# Commande PAPI COMMAND CENTER distante 1.0

Depuis la racine du dépôt, dans un environnement serveur où les secrets sont configurés :

\`\`\`bash
PYTHONPATH=runtime python -m papi_core dashboard-remote
\`\`\`

Options :
- \`--page-size 500\` : lignes lues par page (maximum 1000).
- \`--max-pages 20\` : pages maximum (maximum 20).

Cette commande est distincte de \`dashboard\`, qui reste local. Elle déclenche une lecture distante explicite et utilise uniquement les nouvelles méthodes GET du stockage pour les tâches et le journal d'audit. Elle ne modifie pas Supabase, ne démarre aucun worker et ne déclenche aucune action commerciale ou financière.

Les variables \`SUPABASE_URL\` et \`SUPABASE_KEY\` doivent être définies côté serveur. Les erreurs de configuration ou de lecture renvoient un code de sortie 2 sans afficher de secrets. Une configuration présente ne prouve pas que la clé est valide ni que le schéma SQL a été appliqué.

La commande affiche un instantané composé de lectures indépendantes, pas un snapshot transactionnel. Le registre des agents reste local.
