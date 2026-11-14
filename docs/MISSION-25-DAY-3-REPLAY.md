# Mission 25 — Jour 3 : expiration et anti-rejeu

## Contrôles
- Expiration stricte : `expires_at` doit être postérieur à l'heure de validation.
- Approbation future refusée au-delà d'une tolérance de 60 secondes.
- Durée maximale configurable, 900 secondes par défaut et 86 400 secondes au maximum.
- Identifiant d'approbation déjà consommé refusé.

## Garantie anti-rejeu
Le validateur accepte la collection des identifiants déjà consommés. Il ne la modifie pas et ne garantit pas l'exclusion mutuelle entre processus. Avant production, le consommateur devra effectuer une insertion conditionnelle atomique dans une table avec contrainte unique, dans la même transaction que l'enregistrement de l'autorisation consommée.

## Limite
Aucun stockage de consommation n'est créé dans cette étape ; aucun comportement concurrent n'est revendiqué.
