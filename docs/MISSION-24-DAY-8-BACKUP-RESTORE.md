# Mission 24 — Jour 8 : sauvegarde, restauration et continuité

## Règle de périmètre
Les exercices s'effectuent exclusivement sur une base PostgreSQL jetable. Aucun export, backup ou accès à une base de production/Supabase hébergé n'est autorisé par cette mission.

## Procédure d'exercice
1. Créer une base isolée neuve et appliquer le schéma ainsi que les migrations dans l'ordre.
2. Insérer uniquement des fixtures synthétiques.
3. Produire un dump logique local avec `pg_dump --format=custom`.
4. Créer une seconde base jetable et restaurer avec `pg_restore --exit-on-error`.
5. Vérifier les objets attendus, contraintes, fonctions, privilèges et nombres de lignes de fixtures.
6. Exécuter les tests SQL de contrats après restauration.
7. Détruire les deux bases et les fichiers temporaires de l'exercice.

## Contrôles après restauration
- Présence des tables, index et fonctions attendus.
- Migrations 006 à 009 présentes et exécutables.
- Aucun droit EXECUTE indu sur PUBLIC, anon ou authenticated.
- Les fonctions de diagnostic restent read-only.
- Les tests d'idempotence et de concurrence repartent d'un état propre.

## Continuité et reprise
La restauration est une opération d'administration soumise à approbation humaine. Vérifier le point de restauration, la cible, le propriétaire, les privilèges et l'intégrité avant toute bascule. La bascule et la reprise du trafic ne sont pas automatisées dans cette mission.

## Limites
Aucun backup de production, stockage distant, rotation, chiffrement par clé de production ou test de bascule réelle n'a été effectué. La procédure documente un exercice reproductible, pas une garantie de RPO/RTO.
