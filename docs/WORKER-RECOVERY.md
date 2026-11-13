# Reprise des travaux et limites d'exécution

## Garantie réellement fournie

La file est conçue pour une exécution avec bail et reprises, pas pour une garantie « exactly once ». Une réservation possède un `attempt_id` durable ; les événements d'audit sont distincts par couple tentative/action. Un worker ne peut renouveler ou terminer un job qu'avec le jeton du bail courant. Après expiration ou remplacement du bail, un ancien worker doit être refusé par les fonctions SQL de renouvellement et de terminaison.

## Matrice des pannes

| Point de panne | État observable / reprise | Limite |
| --- | --- | --- |
| Avant le claim | Le job reste dans la file. | Aucun handler n'a été lancé. |
| Après le claim, avant le handler | Le bail expire ; un worker ultérieur peut réclamer le job avec une nouvelle tentative. | La tentative précédente peut ne pas avoir d'événement de fin si le processus a été tué. |
| Échec de l'audit `job.handler_started` | Le handler n'est pas appelé ; le worker tente de marquer l'échec avec `audit_unavailable`. | Si la base est aussi indisponible, la transition échoue et la reprise dépend de l'expiration du bail. |
| Pendant le handler | Une erreur gérée déclenche une transition d'échec ; une perte de bail interrompt le traitement si le handler appelle `ensure_lease`. | Un handler qui ignore `ensure_lease` peut continuer après la perte du bail. |
| Après l'effet métier, avant `complete` | Le job peut être repris après expiration du bail. | L'effet métier peut donc être exécuté une seconde fois. |
| Perte réseau pendant `complete` | Le résultat de la requête peut être inconnu du client. | Il faut relire l'état durable du job avant toute décision manuelle de rejeu. |
| Épuisement des tentatives | La fonction SQL de la file doit terminer le job selon `max_attempts`. | Vérifier l'état et l'historique persistés ; ne pas supposer qu'une tentative a réussi. |

## Obligations des handlers

1. Transmettre `context.attempt_id` aux opérations métier qui acceptent une clé d'idempotence.
2. Utiliser une clé stable par opération logique métier (par exemple l'identifiant de commande), et non une clé différente à chaque retry.
3. Pour un effet externe, enregistrer d'abord une intention durable, puis utiliser l'idempotency key du fournisseur si elle existe.
4. Rendre les opérations répétables ou détecter un effet déjà appliqué avant de le refaire.
5. Appeler `context.ensure_lease()` avant les étapes longues et avant tout effet non idempotent.
6. Ne jamais considérer un timeout réseau comme la preuve que l'opération distante a échoué.

## Audit et diagnostic

- Corréler les événements par `job_id`, `task_id`, `attempt_id` et `worker_id`.
- Un événement `job.handler_started` absent ne prouve pas qu'aucun effet externe n'a eu lieu si un handler a contourné le protocole ou si l'audit était indisponible.
- Un événement `job.completed` absent ne prouve pas que l'effet métier n'a pas été appliqué.
- En cas de transition d'échec impossible, laisser le bail expirer et vérifier ensuite le job, l'historique des tentatives et l'état métier avant tout rejeu manuel.

## Ce qui n'est pas garanti

- Pas de transaction atomique commune entre PostgreSQL, le journal local d'audit et les systèmes externes.
- Pas de livraison exactly-once et pas de garantie d'absence de doublons d'effets métier.
- Pas de reprise automatique d'un effet externe dont le fournisseur ne propose ni clé d'idempotence ni API de consultation.
- Pas de preuve de reprise après crash tant que les scénarios d'intégration avec panne réseau réelle ne sont pas exécutés sur un environnement de test dédié.

## Périmètre

Cette documentation décrit le comportement du code et les précautions nécessaires. Elle n'active aucun worker, ne contacte aucun service externe et ne constitue pas une validation de production.
