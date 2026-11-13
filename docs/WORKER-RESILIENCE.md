# Résilience des workers — politique de reprise

## Portée de cette étape

Le module `papi_core.retry_policy` fournit une décision pure : erreur temporaire
ou permanente, plafond de tentatives, backoff exponentiel plafonné et jitter
injecté. Il ne déclenche ni attente, ni réservation, ni requête, ni handler.
Le paramètre `jitter_sample` est fourni par l'appelant afin que les tests et
les simulations restent déterministes.

## Contrat

- Seuls les codes explicitement présents dans `DEFAULT_RETRYABLE_CODES` sont
  considérés comme transitoires. Tout code inconnu est permanent par défaut.
- `attempt` désigne la tentative qui vient d'échouer et commence à 1.
- Aucune reprise n'est autorisée lorsque `attempt >= max_attempts`.
- Le délai suit un backoff exponentiel, plafonné avant et après jitter.
- Le jitter est borné par `jitter_fraction` et un échantillon fourni dans [0, 1].
- Les paramètres invalides sont rejetés plutôt que corrigés silencieusement.

## Intégration et garanties

Cette étape n'altère pas les RPC SQL existantes ni le comportement de
`ExecutionQueue.fail`. Elle fournit un contrat testable à intégrer plus tard
dans un orchestrateur explicitement gouverné. Les valeurs SQL actuellement
décrites dans `EXECUTION-QUEUE.md` restent la source de vérité opérationnelle
jusqu'à une intégration et des tests d'acceptation distincts.

Les baux et jetons de fencing restent indispensables. Une reprise après
expiration peut conduire à une nouvelle exécution après un effet externe déjà
engagé. Les handlers doivent donc utiliser des clés d'idempotence côté
fournisseur et vérifier le bail avant chaque effet. Cette bibliothèque ne
garantit pas l'exécution exactly-once.

Aucun worker permanent, heartbeat en arrière-plan, DLQ ou mécanisme de
shutdown n'est activé par ce module. Ces sujets nécessitent une intégration
runtime séparée et des tests dédiés. Aucun appel réel à Supabase n'est effectué
par cette politique.
