# Mission 190 — Vérification complète de la chaîne d'ancrage

## Objectif
Empêcher le moteur d'ancrage de publier un checkpoint ou d'accepter une reprise idempotente lorsque la tête courante possède un checkpoint valide isolément mais une chaîne d'ancêtres cassée.

## Changements
- `AnchorClient.publish_checkpoint` valide désormais toute la chaîne depuis la tête courante avant de publier ou d'accepter une reprise.
- La publication échoue en mode fermé si un ancêtre est supprimé, altéré, mal référencé ou si les séquences ne sont pas monotones.
- La tête reste inchangée et aucun nouveau checkpoint n'est écrit lorsque la validation échoue.
- Deux tests de régression couvrent l'extension d'une chaîne avec ancêtre manquant et la reprise idempotente sur une tête dont l'ancêtre manque.
- Documentation de l'ancrage et roadmap mises à jour.

## Validation
- CI GitHub Actions sur le SHA final : à vérifier.
- Tests locaux : non exécutés dans cette session.
- Le stockage mémoire reste exclusivement un adaptateur de test ; aucun service distant n'est connecté.

## Gouvernance
- PR brouillon empilée sur Mission 189 (#366), elle-même ouverte et non fusionnée.
- Aucun agent, worker permanent, scheduler, fournisseur externe, secret, paiement, publication ou déploiement activé.
- Aucun changement sur `main`.
