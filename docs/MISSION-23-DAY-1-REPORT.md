# Mission 23 — Jour 1 : contrats de bail

## Réalisé
- Tests des limites de durée de bail dans le client de file.
- Vérification de la génération d'un jeton distinct par tentative de réservation.
- Vérification du refus de codes d'erreur contenant des caractères ou motifs non autorisés.
- Test du worker lorsque la confirmation du bail échoue : le statut retourné reste `lease_lost`, sans signaler une réussite.
- Les tests unitaires utilisent des doubles locaux ; aucun service externe n'est appelé.

## Limites
Ces tests ne démontrent pas encore l'exclusion mutuelle en concurrence réelle ni la reprise après expiration dans PostgreSQL. Ces scénarios sont prévus pour les prochains jours via le harnais SQL/PostgreSQL jetable.

## Gouvernance
Le worker reste désactivé par défaut. Aucun job métier réel, effet externe, paiement, synchronisation distante, merge ou déploiement n'a été déclenché.
