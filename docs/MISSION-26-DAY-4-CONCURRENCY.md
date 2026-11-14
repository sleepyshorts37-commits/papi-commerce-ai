# Mission 26 — Jour 4 : concurrence et résilience

## Scénarios requis
- Deux sessions consomment le même identifiant : une seule doit obtenir true.
- Un second appel séquentiel doit obtenir false.
- Un autre task_id, handler ou action_class doit obtenir false sans consommer la ligne.
- Une approbation expirée doit rester inutilisable.
- Une erreur d'audit doit annuler la transition de consommation.

## Distinction critique
La consommation atomique empêche la réutilisation d'une autorisation. Elle ne fournit pas exactement-once pour un effet externe. Pour les futures opérations métier, utiliser une clé d'idempotence persistante, une outbox transactionnelle et une vérification du résultat auprès du prestataire.

## Limite de la mission
Les tests SQL séquentiels vérifient les contrats ; la garantie de concurrence découle du verrouillage de ligne et devra être complétée par un test multi-session dédié avant production.
