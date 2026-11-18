# Worker contrôlé

## Ordre d'exécution

`PapiWorker.run_once()` traite au maximum un job et respecte l'ordre suivant :

1. Refuser toute réservation si `execution_enabled` n'est pas exactement `true`.
2. Réserver le job ; la réponse doit contenir un UUID `attempt_id` durable.
3. Charger la tâche et valider strictement l'état d'approbation.
4. Résoudre le handler dans le registre de confiance.
5. Vérifier la signature, la liaison agent/tâche/handler et l'anti-rejeu.
6. Émettre le principal authentifié, puis appliquer la politique métier.
7. Renouveler le bail détenu par le worker.
8. Écrire durablement `job.handler_started` avant d'appeler le handler.
9. Passer `attempt_id`, le principal et le callback de contrôle du bail au handler.
10. Confirmer la transition terminale avec le même jeton de bail.

Un refus avant la fin de la vérification cryptographique reste attribué au worker système. Un refus de politique après authentification conserve le principal vérifié et produit `job.blocked` avec `permission_denied`.

## Journal d'audit worker

Chaque événement worker contient `job_id`, `task_id`, `attempt_id`, `worker_id`, l'acteur et l'agent authentifié lorsqu'il existe, l'action, l'horodatage, le résultat et un identifiant de déduplication. La déduplication est calculée à partir de `job_id + attempt_id + action` : une nouvelle tentative ne doit donc pas être masquée par un événement d'une tentative précédente.

L'écriture de `job.handler_started` est fail-closed : si elle échoue, le handler n'est pas invoqué et le job est envoyé vers une transition d'échec contrôlée. Les événements terminaux restent best-effort après confirmation durable de la file ; une panne d'audit à ce stade doit être signalée comme une limite de traçabilité, pas comme une annulation de la transition.

## Garanties et limites

- Le fencing du bail protège les transitions de réservation, de renouvellement, de complétion et d'échec.
- Un handler doit appeler le callback de contrôle du bail immédiatement avant chaque effet externe et périodiquement pendant un traitement long.
- Les identifiants de tentative et l'idempotence locale ne garantissent pas l'exécution exactly-once d'un effet externe. Les systèmes externes doivent fournir leur propre clé d'idempotence ou mécanisme de déduplication.
- Un crash après un effet externe mais avant la confirmation durable peut conduire à une reprise ; ce cas doit être traité par idempotence métier.
- Le worker reste désactivé par défaut. Aucun worker réel n'est activé ou déployé par cette documentation.

## Utilisation locale

Le worker est appelé explicitement une fois par le processus qui l'héberge. Il ne crée ni boucle infinie, ni planificateur, ni service permanent. Le registre doit être construit par le code de confiance et la politique chargée depuis un fichier protégé.
