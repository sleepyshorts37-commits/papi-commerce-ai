# Mission 26 — Jour 1 : modèle relationnel et menace

## Contrat relationnel
Le registre `papi_approval_ledger` conserve l'identifiant unique, la tâche liée, le handler, la classe d'action, l'identité de l'approbateur, les horodatages et les métadonnées de consommation. Une clé étrangère empêche de créer une approbation pour une tâche inexistante.

## Menaces couvertes
- Réutilisation d'une approbation sur une autre tâche ou action.
- Consommation après expiration.
- Consommations concurrentes.
- Modification directe de l'historique par un agent.
- Audit incomplet si l'écriture d'événement échoue.

## Frontière de confiance
Le backend doit authentifier le propriétaire avant d'appeler la RPC d'émission. La base impose les formats, les limites temporelles et les permissions, mais ne remplace pas l'authentification MFA ou la vérification de session.

## Résultat
Contrat relationnel et limites de sécurité définis. Aucune base hébergée n'est utilisée.
