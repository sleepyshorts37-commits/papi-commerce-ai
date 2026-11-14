# Mission 26 — Jour 4 : concurrence et résilience

## Scénarios requis
- Deux sessions consomment le même identifiant : une seule doit obtenir true.
- Un second appel séquentiel doit obtenir false.
- Un autre task_id, handler ou action_class doit obtenir false sans consommer la ligne.
- Une approbation expirée doit rester inutilisable.
- Une erreur d'audit doit annuler la transition de consommation.

## Distinction critique
La consommation atomique empêche la réutilisation d'une autorisation. Elle ne fournit pas exactement-once pour un effet externe. Pour les futures opérations métier, utiliser une clé d'idempotence persistante, une outbox transactionnelle et une vérification du résultat auprès du prestataire.

## Validation de concurrence
Le script `tests/sql/test_approval_ledger_concurrency.sh` lance deux sessions PostgreSQL simultanées et exige exactement un résultat `true` et un résultat `false`. Le workflow CI l'exécute sur les deux bases jetables.

## Limite de la mission
Le test démontre le comportement de cette RPC dans PostgreSQL local ; il ne remplace pas un test de charge, une revue des droits de production ou un test de panne réseau.
