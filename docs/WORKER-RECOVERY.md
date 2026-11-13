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
| Échec transitoire (stockage, réseau, handler) | Le worker transmet `retryable=true` ; la file planifie une reprise avec backoff jusqu'à `max_attempts`. | Une opération métier déjà appliquée doit être protégée par une clé d'idempotence stable. |
| Échec terminal (identité, permission, validation) | Le worker transmet `retryable=false` ; le job passe immédiatement à `failed`. | Une correction humaine ou de configuration est nécessaire avant de créer une nouvelle tâche. |
| Épuisement des tentatives | La fonction SQL termine le job selon `max_attempts`, y compris si le dernier bail expire. | Vérifier l'état et l'historique persistés ; ne pas supposer qu'une tentative a réussi. |

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
- Si la réponse réseau de `complete` est perdue, relire le job et son historique avant toute reprise ; une seconde commande `complete` avec l'ancien bail ne doit pas réécrire un job terminal.
- Le worker renvoie désormais le résultat réel de la file dans `queue_status` ; il ne confond plus une erreur gérée programmée pour retry avec un état terminal du job.
- En cas de transition d'échec impossible, laisser le bail expirer et vérifier ensuite le job, l'historique des tentatives et l'état métier avant tout rejeu manuel.

## Ce qui n'est pas garanti

- Pas de transaction atomique commune entre PostgreSQL, le journal local d'audit et les systèmes externes.
- Pas de livraison exactly-once et pas de garantie d'absence de doublons d'effets métier.
- Pas de reprise automatique d'un effet externe dont le fournisseur ne propose ni clé d'idempotence ni API de consultation.
- Les tests CI simulent un crash après l'effet métier et avant `complete`, un retry idempotent avec clé stable, une réponse de complétion ambiguë et la séparation des erreurs transitoires/terminales. Cela valide les transitions PostgreSQL et le contrat local, mais ne simule pas une coupure réseau réelle entre plusieurs fournisseurs.
- Pas de preuve de reprise après crash dans des systèmes externes réels tant que les scénarios de panne réseau ne sont pas exécutés dans un environnement de test dédié.

## Périmètre

Cette documentation décrit le comportement du code et les précautions nécessaires. Elle n'active aucun worker, ne contacte aucun service externe et ne constitue pas une validation de production.


## Politique de reprise mise en œuvre

La RPC additive `papi_fail_job(..., p_retryable)` sépare les erreurs transitoires des erreurs terminales. Les erreurs de stockage, de file et d'exécution de handler sont réessayables ; les échecs d'authentification, de permission et de validation du worker sont terminaux. La surcharge historique à quatre arguments reste présente pour la compatibilité, tandis que le worker utilise explicitement le paramètre booléen.

Les tests CI PostgreSQL créent un effet métier simulé avec une contrainte unique sur une clé d'idempotence stable, expirent le bail après cet effet, réclament une nouvelle tentative, puis vérifient qu'un second passage ne duplique pas l'effet. Ils vérifient également le statut `lease_expired` de l'ancienne tentative et le refus d'une seconde complétion après la première transition terminale.


## Concurrence des claims et fencing des baux

La réservation SQL utilise une sélection `FOR UPDATE SKIP LOCKED` : deux transactions concurrentes ne doivent pas réserver la même ligne pendant que le premier claim détient son verrou. Chaque réservation effective crée un nouvel `attempt_id` et remplace le jeton de bail. Le worker précédent est alors clôturé dans l'historique comme `lease_expired`.

Le renouvellement est conditionnel : job toujours `running`, propriétaire identique, jeton identique et bail non expiré. Un renouvellement refusé (`false`) signifie que le worker ne possède plus un bail valide ; il doit cesser les opérations métier protégées. La complétion et l'échec appliquent le même contrôle de propriété/jeton et la vérification de validité temporelle.

La CI PostgreSQL jetable vérifie deux claims simultanés sur deux jobs prêts : une transaction garde le verrou du premier job tandis qu'une seconde transaction doit en réserver un autre. Elle vérifie également le refus de renouvellement et de complétion par un worker obsolète. Ce test valide le comportement de verrouillage PostgreSQL dans ce scénario ; il ne prouve pas l'absence de toute course dans les systèmes externes ni l'exécution exactly-once.
