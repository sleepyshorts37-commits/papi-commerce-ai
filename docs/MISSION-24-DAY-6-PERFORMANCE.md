# Mission 24 — Jour 6 : performance PostgreSQL

## Objectif et périmètre
Établir une méthode reproductible d'observation des fonctions d'état et de diagnostic sur PostgreSQL jetable. Aucun seuil issu d'un environnement de production n'est supposé.

## Mesures à effectuer
Sur une base isolée chargée avec les migrations 006 à 009 :
1. Capturer `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` pour les appels de santé, résumé d'erreurs et diagnostic.
2. Répéter les mesures avec des volumes de fixtures croissants (petit, moyen, grand), en conservant le même matériel CI.
3. Noter durée, blocs lus/atteints, lignes estimées/réelles et éventuels parcours séquentiels.
4. Pour les chemins de réservation, inspecter le plan de la fonction de claim existante sans modifier sa sémantique de verrouillage.
5. Comparer les résultats avant/après tout index candidat, puis conserver uniquement un index dont le bénéfice est démontré et dont le coût d'écriture est acceptable.

## Seuils d'observation
Les seuils initiaux sont des déclencheurs d'investigation, pas des SLO : hausse de latence supérieure à 2x entre deux tailles comparables, croissance soutenue des blocs lus, écart estimation/réalité supérieur à 10x, ou apparition d'un tri/scan coûteux sur le chemin chaud. Toute valeur doit être recalibrée sur un environnement représentatif avant usage opérationnel.

## Résultat
Aucun index supplémentaire n'est justifié par les seules données disponibles dans cette tâche. La CI actuelle valide les contrats fonctionnels, pas un benchmark de production. Le script `tests/sql/test_queue_performance_observation.sql` fournit des plans observables sur la base jetable.

## Limites
Les durées CI dépendent de la charge partagée et ne sont pas des mesures de capacité. Aucun scheduler, collecte continue ou export externe n'est activé.
