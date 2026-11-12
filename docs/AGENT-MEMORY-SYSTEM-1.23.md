# PAPI AGENT MEMORY SYSTEM 1.23

## Fonctionnalités
- Catégories : expérience, décision, connaissance, leçon, erreur.
- Entrées structurées avec titre, contenu, tags, référence source et visibilité.
- Permission explicite `manage_own_memory`, agent actif et profil complet requis.
- Chaque agent ne peut proposer que sa propre mémoire.
- Rappel lexical local, limité aux entrées privées de l'agent demandeur.
- Le centre ne projette que les événements `agent.memory.recorded` explicitement présents dans l'audit.

## Confidentialité
Les coordonnées e-mail/téléphone et les termes sensibles courants (mot de passe, secret, token, clés API, données de carte) sont refusés. Les événements sont validés par le contrôle de sécurité du journal. Cette détection est une barrière élémentaire, pas un système DLP complet ; aucune donnée client ou donnée personnelle ne doit être stockée.

## Limites
Les candidats ne sont pas persistés. Aucun stockage mémoire durable, chiffrement au repos, moteur sémantique/embedding, synchronisation, partage entre agents ou effacement automatique n'est fourni dans cette phase. Les visibilités team/company sont des métadonnées, pas un partage opérationnel. Aucun agent n'est activé ni déployé.

Les identités existantes restent planifiées/incomplètes ; elles ne disposent donc pas des prérequis pour utiliser cette mémoire. Tests ajoutés, non exécutés ici.
