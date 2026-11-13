# Persistance partagée de la mémoire et de PAPI CHAT

## Migration 004

`infra/supabase/migrations/004_shared_collaboration.sql` ajoute deux tables PostgreSQL :
- `papi_memory_events` : événements de mémoire append-only (`remember` et `supersede`), avec portée `shared` ou `agent`, validation de forme et sensibilité normale uniquement.
- `papi_chat_messages` : messages internes directs ou diffusés, avec tailles et types bornés.

Les deux tables activent RLS, refusent les droits aux rôles `anon` et `authenticated`, et n'accordent que SELECT/INSERT à `service_role`. Des triggers refusent UPDATE et DELETE : l'historique reste append-only.

## Limites actuelles

Cette livraison établit le contrat SQL, pas encore la synchronisation runtime. Les fonctions locales `memory.py` et `chat.py` continuent à utiliser leurs journaux locaux. Aucun client Supabase n'est activé, aucune migration distante n'est exécutée et aucun secret n'est ajouté au dépôt.

La prochaine étape devra implémenter des adaptateurs injectables, le filtrage d'accès par agent, la pagination stable et des tests PostgreSQL de concurrence avant d'autoriser une synchronisation entre instances.

## Adaptateurs — Phase 2, jour 2

Le module `runtime/papi_core/shared_persistence.py` fournit deux adaptateurs opt-in :
- `SharedMemoryAdapter` : écrit les événements `remember` / `supersede` et lit les événements autorisés avec pagination stable.
- `SharedChatAdapter` : écrit les messages et lit uniquement les messages directs de l'agent authentifié ou les diffusions `all`.

Les adaptateurs exigent un `SupabaseStore` injecté depuis le backend de confiance. Les lectures exigent un objet `AuthenticatedAgentPrincipal` émis par la frontière d'authentification interne ; une chaîne contenant un identifiant d'agent est refusée. Les filtres d'accès sont appliqués dans la requête PostgREST avant le retour des lignes.

**Non-activation volontaire :** les fonctions publiques existantes de `memory.py` et `chat.py` restent locales et inchangées. Aucun appel distant n'est déclenché automatiquement. Le déploiement, les identifiants, la migration distante, la synchronisation et les workers restent désactivés. Les tests utilisent un magasin simulé et ne contactent aucun service externe.
