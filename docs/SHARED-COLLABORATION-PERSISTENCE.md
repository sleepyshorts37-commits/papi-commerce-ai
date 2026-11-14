# Mission 21 — Mémoire partagée et PAPI CHAT

## Jour 1/5 : contrat SQL de persistance inter-instances

Cette journée pose uniquement les fondations PostgreSQL de la mémoire et de la messagerie internes. Elle ne connecte pas encore les modules Python locaux au stockage distant.

### Tables
- `papi_memory_events` : journal d'événements mémoire `remember` / `supersede`, avec identifiants, auteur, source, confiance, portée, tags et sensibilité.
- `papi_chat_messages` : messages directs ou diffusés, avec identifiant, date, expéditeur, destinataire, sujet, corps et type.

### Garanties
- Contraintes SQL sur identifiants, catégories, portée, sensibilité, tailles et types.
- RLS activée ; droits révoqués pour `public`, `anon` et `authenticated`.
- Seul le rôle backend `service_role` reçoit SELECT/INSERT.
- Triggers append-only interdisant UPDATE et DELETE, y compris au rôle serveur.
- Index pour les recherches par mémoire, auteur/portée et destinataire/date.
- Rollback refusé dès qu'une des tables contient des données ; aucun effacement implicite de l'historique.

### Limites conservées
Les modules `memory.py` et `chat.py` continuent d'utiliser leurs journaux JSONL locaux. Aucun adaptateur distant, transfert de données, secret, connexion Supabase hébergée, activation d'agent ou synchronisation automatique n'est ajouté. Le SQL est vérifié sur PostgreSQL jetable dans GitHub Actions uniquement.

### Suite prévue
Les journées suivantes pourront ajouter les adaptateurs backend injectables, l'isolation par identité authentifiée, la pagination stable, l'idempotence, les contrôles de concurrence et les tests de cohérence. Ces étapes ne doivent jamais contourner les permissions ni activer une synchronisation sans décision explicite.
