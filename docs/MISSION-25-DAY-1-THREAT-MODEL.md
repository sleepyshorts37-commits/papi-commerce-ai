# Mission 25 — Jour 1 : modèle de menace et contrat d'approbation

## Décision d'architecture
Une approbation n'est pas un booléen de tâche. C'est une attestation émise par une couche d'identité de confiance, à usage limité et liée à une opération unique.

## Menaces couvertes
- Un agent modifie `approval_status` ou fabrique un champ d'approbation dans son payload.
- Une approbation valide pour une tâche est réutilisée sur une autre.
- Une autorisation donnée pour un handler est réutilisée pour un autre handler.
- Une approbation ancienne est rejouée après expiration.
- Une approbation déjà consommée est présentée une seconde fois.
- Un horodatage sans fuseau ou incohérent contourne la fenêtre de validité.

## Contrat
Champs obligatoires : `approval_id`, `task_id`, `handler`, `action_class`, `decision`, `approved_by`, `approved_at`, `expires_at`. Le propriétaire est identifié par `policy.owner_id`. La tâche doit être `in_progress`. La durée maximale par défaut est 900 secondes.

## Frontière de confiance
Le module reçoit une attestation depuis une couche d'authentification externe déjà validée. Il ne vérifie ni session, ni signature, ni MFA. Il ne doit jamais accepter comme source d'approbation un message d'agent, un contenu de job ou une valeur issue d'un modèle IA.

## Résultat
Le contrat est défini. Aucun canal d'approbation ni service externe n'est connecté.
