# Mission 33 — Contrat d'exploitation et gates de synchronisation

## Invariants
- Un plan est une proposition, pas une commande.
- Le plan contient des identifiants, types, opérations, digest et statut ; jamais le contenu mémoire ou chat.
- Tout conflit bloque le plan entier ; aucun arbitrage automatique.
- L'approbation propriétaire Ed25519 est liée au digest exact, à la destination et à la liste ordonnée d'action IDs.
- L'agent qui produit le plan ne peut pas s'approuver lui-même.
- La vérification de signature consomme un nonce anti-rejeu ; le backend consomme ensuite l'approbation par la RPC atomique.
- Un snapshot incomplet, une identité invalide ou un résultat réseau incertain bloque la suite.

## Contrat d'approbation livré
1. Le backend construit un plan et conserve son digest.
2. Le propriétaire signe une enveloppe contenant `approval_id`, `task_id`, `handler`, `action_class`, `decision`, `approved_by`, les dates, `plan_digest`, `destination_instance` et `action_ids`.
3. `verify_sync_plan_approval` vérifie Ed25519, le registre de clés, le nonce, l'identité propriétaire, la tâche et la portée exacte.
4. Le backend appelle `papi_consume_sync_approval` avec le même digest, la destination et la liste d'actions. Une seule transaction peut consommer l'approbation.
5. Cette mission n'inclut pas de worker d'application de synchronisation. La consommation n'exécute donc aucune copie.

## États d'exécution futurs
`proposed → approved → applying → completed`
Branches de sortie : `blocked`, `partial`, `expired`. Le présent code livre la validation et la consommation d'approbation, pas l'exécuteur ni les transitions d'effet.

## Idempotence et reprise
Chaque action conserve un identifiant immuable dérivé du plan, de l'agent, de la destination, de l'opération et de la ressource. Le futur exécuteur devra enregistrer clé d'idempotence et état d'effet dans la même transaction quand possible. Après un timeout, lire l'état distant avant tout retry. Ne jamais conclure à l'échec d'un effet uniquement parce que la réponse réseau manque.

## Observabilité sans contenu
Journaliser correlation ID, plan digest, action ID, instance, type d'opération, durée, résultat catégorisé et compteur de retry. Ne jamais journaliser corps de message, titre/contenu mémoire, credentials, URL avec paramètres sensibles ou payload complet.

## Gates avant production
1. Projet Supabase distant de test autorisé et accès provisionné.
2. Identité propriétaire et clés gérées hors dépôt.
3. Tests réels entre instances et concurrence réussis.
4. Sauvegarde et restauration démontrées sur environnement isolé.
5. Revue indépendante et plan de rollback approuvés.
6. Exécuteur de synchronisation développé et audité dans une mission distincte.
7. Autorisation distincte de mise en service.

Aucun de ces gates n'est implicitement validé par la PR. Aucun transfert, worker, déploiement ou appel distant n'est activé.

## Sauvegarde et restauration — procédure opérateur

À exécuter uniquement dans un environnement de test autorisé, avec des secrets injectés depuis un gestionnaire sécurisé (jamais dans l'historique shell partagé ni dans Git).

```bash
pg_dump --format=custom --no-owner --no-acl \
  --file="$BACKUP_DIR/papi-$(date -u +%Y%m%dT%H%M%SZ).dump" \
  "$PAPI_DATABASE_URL"
pg_restore --list "$BACKUP_FILE" >/dev/null
createdb "$RESTORE_DATABASE"
pg_restore --no-owner --no-acl --dbname="$RESTORE_DATABASE" "$BACKUP_FILE"
```

Après restauration, vérifier les migrations attendues, les privilèges RLS, les fonctions RPC et les comptages de lignes. Ne jamais restaurer par-dessus une base active sans approbation explicite et fenêtre de maintenance. Les tests CI utilisent des bases jetables ; aucune sauvegarde d'un projet hébergé n'a été créée par cette mission.

## Arrêt d'urgence et reprise

- Désactiver le point d'entrée applicatif de synchronisation dans la configuration de déploiement ; aucune variable d'activation n'est livrée par cette PR.
- Suspendre les jobs de synchronisation éventuels côté orchestrateur et conserver les journaux d'audit.
- Ne pas supprimer les approbations ni les reçus d'idempotence : ils sont nécessaires à l'analyse d'incident.
- En cas de résultat réseau inconnu, ne pas réémettre l'action ; interroger l'état cible et faire arbitrer par le propriétaire.
- Réouvrir uniquement après analyse de cause racine, restauration testée et approbation distincte.

## Rotation et révocation des identités

Le module `papi_core.identity_ed25519` fournit `rotate_ed25519_agent` et `revoke_ed25519_agent`. Exécuter ces opérations depuis un environnement administrateur local sécurisé ; vérifier la nouvelle version de clé publique dans le registre, tester une signature fraîche, puis vérifier que les anciennes signatures et nonces rejoués sont refusés. Les clés privées restent sur l'instance et ne sont jamais copiées dans le dépôt.

## Télémétrie recommandée

Mesures agrégées : nombre de plans créés, plans bloqués par conflit, approbations refusées par motif, approbations consommées, expirations, tentatives de rejeu, latence de lecture, erreurs réseau catégorisées et retries. Les labels ne doivent contenir ni identifiant client, ni contenu, ni secret. Utiliser un correlation ID aléatoire et le digest du plan pour relier les événements d'audit.
