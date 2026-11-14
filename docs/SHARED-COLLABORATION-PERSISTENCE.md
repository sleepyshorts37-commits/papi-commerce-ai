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


## Jour 2/5 : adaptateurs serveur injectables

Le module `runtime/papi_core/shared_collaboration.py` ajoute une façade explicite sur le stockage Supabase existant.

### Garanties
- Le store est injecté : aucun client, secret, appel réseau ou synchronisation n'est créé implicitement.
- Chaque opération exige un `AuthenticatedAgentPrincipal` non forgeable par une simple chaîne.
- L'identité de l'auteur mémoire et de l'expéditeur de message est dérivée du principal authentifié, jamais d'un champ libre.
- La lecture mémoire interroge séparément les portées partagées et privées de l'agent ; la requête privée est filtrée côté serveur par `actor`.
- La lecture PAPI CHAT est filtrée côté serveur sur les messages diffusés et ceux adressés à l'agent.
- Les catégories de décision, portées owner, données restreintes et contenus ressemblant à des secrets restent refusés.
- Les opérations sont limitées à des tables et colonnes explicitement autorisées.

### Limites volontaires
- Les fonctions locales JSONL de `memory.py` et `chat.py` ne changent pas : leur comportement reste le défaut.
- L'adaptateur ne s'active que si un backend serveur et un principal validé sont explicitement fournis.
- Aucun transfert des anciens journaux, synchronisation automatique, worker, notification, paiement ou action externe n'est lancé.
- La pagination durable, l'idempotence et les tests de bout en bout PostgreSQL sont réservés aux journées suivantes.
- La clé `service_role` ne doit exister que dans l'environnement serveur protégé.

Les tests unitaires utilisent un faux store sans réseau ni projet Supabase hébergé.
