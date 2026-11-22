# Mission 193 — Rejeter les clés JSON dupliquées dans le journal d'audit

## Constat

Le lecteur du journal utilisait le comportement JSON standard « dernière clé gagnante ». Une ligne pouvait donc contenir deux clés identiques, être décodée en un objet apparemment valide, puis passer le contrôle de hash si la dernière valeur correspondait à l'événement initial. Cela rendait le texte source ambigu malgré une chaîne de hash cohérente sur l'objet décodé.

## Modifications

- Ajoute un hook de décodage qui refuse les clés répétées dans tout objet JSON, y compris les objets imbriqués de `details`.
- Conserve la compatibilité avec les lignes historiques valides : aucun ordre de clés ni espacement canonique n'est imposé au journal existant.
- Ajoute une régression pour une clé dupliquée de premier niveau et une clé dupliquée imbriquée. Dans les deux cas, le test vérifie que le décodeur JSON standard produit le même objet apparent avant que le lecteur strict refuse la ligne.
- Actualise la documentation du journal et la roadmap.

## Validation vérifiée

Sur le SHA de code et de documentation initial `9de039051aa44bb3a79c34de706450e6c715719a`, les trois workflows GitHub Actions ont terminé avec succès :

- [PAPI core tests — run 45023396064](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45023396064) : **228 tests réussis**, 0 échec ; le test `test_read_rejects_duplicate_json_keys_at_all_nesting_levels` apparaît explicitement avec le résultat `ok`.
- [PAPI registry validation — run 45023396070](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45023396070) : succès.
- [PAPI documentation checks — run 45023396162](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45023396162) : succès.

Le workflow core a aussi réussi les étapes de cohérence des dépendances, d'audit du graphe runtime et les vérifications sur PostgreSQL jetable (schéma, fixtures legacy, migration, concurrence des claims et rollback). Tests locaux : non exécutés.

## Gouvernance et limites

- Branche dédiée empilée sur la tête de Mission 192 (#369).
- Aucun changement sur `main`, aucune fusion ni aucun déploiement.
- Aucun agent, worker ou scheduler réel activé.
- Aucun service externe, secret, compte, paiement ou effet commercial.
- Le hash local détecte les altérations par rapport à une chaîne connue, mais ne protège pas contre un attaquant contrôlant simultanément le journal et tous les checkpoints locaux.
