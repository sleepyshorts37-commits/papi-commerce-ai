# PAPI APPROVAL CENTER 1.17

## Objectif
Créer un registre centralisé des demandes d'approbation et des décisions du propriétaire, avec historique d'audit append-only en lecture seule.

## Événements pris en charge
- `approval.requested` : enregistre la nature, la description, le risque, le demandeur et l'approbateur requis.
- `approval.approved` : décision positive de l'approbateur désigné.
- `approval.rejected` : refus de l'approbateur désigné.

Le centre reconstruit l'état courant (pending/approved/rejected) depuis les événements d'audit. Une demande ne peut recevoir qu'une décision, et seul l'acteur explicitement désigné comme approbateur peut décider.

## Préparation d'une décision
`build_approval_decision_candidate` produit un événement candidat après vérification du statut pending et de l'identité de l'acteur propriétaire configurée par l'appelant. L'événement n'est pas persisté.

## Limites de sécurité
- Aucun appel à `append_event` dans ce module.
- Aucune action métier déclenchée par une approbation.
- Une décision approuvée signifie uniquement que la demande a été validée ; elle ne prouve pas qu'une action a été exécutée ni ne l'exécute.
- Les secrets et données sensibles ne sont pas acceptés dans les descriptions.
- L'intégration à un véritable canal d'authentification du propriétaire, la persistance contrôlée et l'interface de revue restent à construire.

Tests ajoutés mais non exécutés dans cet environnement. Aucune migration Supabase, aucun déploiement, aucun agent ou worker activé.
