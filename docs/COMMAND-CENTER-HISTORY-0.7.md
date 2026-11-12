# PAPI COMMAND CENTER — historique des agents 0.2

Le tableau de bord local reste en lecture seule et agrège désormais les indicateurs de chaque agent à partir de data/events.jsonl, le journal JSONL append-only.

## Indicateurs
- Affectations reçues.
- Transitions effectuées par l'agent.
- Tâches terminées, bloquées ou annulées par l'agent comme acteur d'événement.
- Nombre d'événements d'audit pris en compte.
- Totaux agrégés et détail par identifiant d'agent.

## Source et absence de données
Le chemin du journal peut être fourni avec le paramètre audit_path de build_command_center. Si le fichier n'existe pas ou ne contient aucun événement, le tableau indique no_events et les métriques restent à zéro. Un journal invalide provoque une erreur explicite ; il n'est jamais ignoré silencieusement.

## Contrôles
L'intégration ne crée ni n'altère d'événement, n'affecte aucune tâche, ne démarre aucun worker et n'envoie aucune notification. Elle ne rend pas les agents actifs. Les données historiques réelles n'existeront qu'après utilisation effective du runtime.
