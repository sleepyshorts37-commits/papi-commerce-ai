# Mission 25 — Jour 5 : tests adversariaux et clôture

## Couverture prévue
- Approbation valide et strictement liée à une action.
- Approbateur différent du propriétaire.
- Tâche, handler ou classe d'action différente.
- Identifiant déjà consommé.
- Approbation expirée ou de durée excessive.
- Horodatage sans fuseau.
- Décision en attente ou refusée.
- Tâche qui n'est pas en cours.

## Résultat attendu
La suite doit démontrer le refus par défaut des cas non conformes et l'acceptation du seul cas nominal. Les tests sont déterministes et n'utilisent aucun service externe.

## Limites résiduelles
L'identité de l'approbateur doit être vérifiée par une couche d'authentification fiable. L'anti-rejeu multi-processus exige un stockage atomique durable. La revue ne constitue pas une certification de sécurité. Aucun agent n'est déployé et aucune action réelle n'est effectuée.
