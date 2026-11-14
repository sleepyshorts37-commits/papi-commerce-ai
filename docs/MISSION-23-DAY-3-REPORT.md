# Mission 23 — Jour 3 : concurrence multi-session

## Objectif
Prouver le comportement concurrent de la réservation PostgreSQL avec deux sessions indépendantes qui se chevauchent réellement.

## Scénario automatisé
1. Préparer deux jobs isolés dans la base PostgreSQL jetable de CI.
2. La session A appelle `papi_claim_job` dans une transaction et conserve son verrou de ligne pendant trois secondes.
3. Après 500 ms, la session B appelle la même fonction sur une autre connexion.
4. Vérifier que les deux sessions obtiennent chacune un job différent et des jetons de bail différents.
5. Terminer chaque job avec le worker propriétaire et son jeton courant.

## Portée et limites
- Le test exerce plusieurs connexions PostgreSQL simultanées et le verrouillage `FOR UPDATE SKIP LOCKED`.
- Les fixtures sont limitées à la base CI jetable.
- Aucun worker permanent, scheduler, message, paiement, transfert ou effet externe n'est activé.
- La validation finale dépend de la réussite de GitHub Actions ; ce rapport ne déclare pas le test validé avant le résultat CI.
