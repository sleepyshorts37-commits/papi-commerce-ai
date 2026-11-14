# PAPI COMMERCE AI — Mission 20 : clôture technique

## Objectif de la mission
Relier les sorties PAPI AI WORKERS à PAPI COMMAND CENTER au moyen de contrats de données explicites, d'un stockage central optionnel, d'une synchronisation idempotente et de contrôles de cohérence.

## Livrables consolidés
1. **Jour 1 — Vue de supervision** : rapport agrégé des plateformes, relais humains et résultats de rentabilité, en lecture seule.
2. **Jour 2 — Adaptateurs d'entrée** : normalisation des formats des workers, distinction entre source absente et collection vide, rejet des entrées contradictoires.
3. **Jour 3 — Registre central** : snapshots versionnés, reçus d'événements, journal d'audit et RPC transactionnelle PostgreSQL.
4. **Jour 4 — Connecteur serveur** : adaptateur Supabase explicite, lectures bornées des trois domaines et activation optionnelle du Command Center.
5. **Jour 5 — Durcissement** : correction des régressions révélées par la CI, compatibilité du diagnostic, validation des confirmations sensibles, compatibilité du seuil de rentabilité historique et sérialisation des tentatives partageant une clé d'idempotence.

## Invariants de sécurité
- Le mode local reste le mode par défaut.
- Les accès Supabase ne sont possibles qu'avec un stockage serveur explicitement injecté.
- Les tables workers restent protégées par RLS et inaccessibles aux rôles `anon` et `authenticated`.
- La RPC utilise `SECURITY INVOKER` et n'est exécutable que par `service_role`.
- Les secrets ne sont ni affichés, ni enregistrés dans les payloads workers.
- La clé `service_role` ne doit jamais être fournie à un navigateur, une application mobile ou un agent client.
- Les versions optimistes protègent contre les mises à jour concurrentes ; le verrou transactionnel par clé d'idempotence sérialise les rejeux simultanés.
- Aucun agent, scheduler, paiement, notification ou action externe n'est activé par ce lot.

## Validation et limites
La CI GitHub Actions a bien été déclenchée sur la PR du Jour 4. Elle a exécuté 278 tests Python et a mis en évidence trois échecs préexistants/régressions de compatibilité dans le lot : alias de diagnostic, détection de texte sensible dans le relais humain et nom historique du seuil horaire. Le Jour 5 corrige ces trois points et ajoute des assertions de régression. La validation finale doit être lue sur le dernier workflow de la PR du Jour 5 ; le test PostgreSQL jetable ne doit être considéré comme validé que si son étape CI passe.

Aucun projet Supabase hébergé n'a été contacté ou modifié dans cette mission. Aucun merge ni déploiement n'a été effectué.
