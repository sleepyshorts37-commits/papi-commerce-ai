# Mission 24 — Jour 9 : résilience et scénarios de panne

## Couverture existante dans les tests
- Concurrence de réservation PostgreSQL sur sessions distinctes et verrouillage SKIP LOCKED.
- Jetons de bail distincts et fencing du propriétaire.
- Refus des opérations lorsque le bail n'est plus valide.
- Idempotence et limites de tentatives via les contrats SQL de la file.
- Crash/retry et validation d'événements dans les tests SQL déjà présents.

## Scénarios additionnels à vérifier dans l'environnement jetable
1. Interrompre une session cliente pendant une transaction de réservation ; confirmer que PostgreSQL libère les verrous à la fermeture de session.
2. Simuler une indisponibilité de la base en arrêtant uniquement le conteneur PostgreSQL jetable ; vérifier que le client reçoit une erreur contrôlée et ne lance pas de boucle de retry.
3. Redémarrer le conteneur jetable et rejouer les tests depuis un état fixture propre.
4. Rejouer la même clé d'idempotence et vérifier qu'aucun doublon n'est créé.
5. Présenter un ancien jeton après expiration ou réattribution du bail et confirmer qu'il ne peut pas finaliser le travail.
6. Vérifier que les tentatives plafonnées n'aboutissent pas à une réservation infinie.

## Résultat et limites
Les tests CI existants valident la concurrence et les invariants de bail/idempotence sur PostgreSQL jetable. Le scénario de coupure/redémarrage du conteneur n'est pas exécuté par le workflow actuel ; il reste un exercice opérateur documenté, non présenté comme validé. Aucun worker permanent, boucle de polling ou reprise automatique n'est ajouté.
