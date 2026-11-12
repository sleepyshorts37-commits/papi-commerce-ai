# Vérification Supabase 1.1

Commande explicite :

\`\`\`bash
PYTHONPATH=runtime python -m papi_core supabase-check
\`\`\`

Le contrôle effectue deux requêtes GET limitées à une ligne :
- \`papi_tasks\` (colonne id) ;
- \`papi_audit_events\` (colonne event_id).

Il indique si les deux tables sont lisibles par les identifiants fournis. Aucun contenu de tâche ou d'événement n'est exposé dans le rapport. Aucun secret n'est affiché et aucune écriture n'est effectuée.

Un résultat \`ready\` prouve uniquement que ces deux requêtes de lecture ont répondu. Il ne valide pas les fonctions RPC, l'ensemble du schéma, les sauvegardes, la sécurité opérationnelle complète ni le démarrage des agents. En cas d'échec, le détail est volontairement générique pour ne pas exposer d'informations d'infrastructure.
