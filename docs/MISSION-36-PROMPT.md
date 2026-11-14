# Mission 36 — Fiabilité du journal mémoire et intégrité des événements

## Objectif
Renforcer le journal append-only de mémoire PAPI afin qu'aucune recherche ou opération d'archivage ne consomme un événement malformé, ambigu, sensible ou référencé de façon incohérente. Fiabiliser l'écriture face aux écritures système partielles.

## Jour 1 — Audit
- Examiner les contrats existants de mémoire, worker, stockage, permissions et tests.
- Cartographier les champs obligatoires des événements remember/supersede.
- Identifier les lacunes de validation à la lecture et à l'écriture.

## Jour 2 — Validation du journal
- Valider la structure complète de chaque type d'événement.
- Valider les horodatages ISO-8601 avec fuseau.
- Valider catégories, portées, sensibilité, confiance, tags, source et contenu.
- Refuser les données sensibles imbriquées et les valeurs non finies.

## Jour 3 — Cohérence append-only
- Détecter les IDs d'événements et de mémoires dupliqués.
- Refuser les archivages orphelins ou répétés.
- Préserver l'historique sans réécriture des événements existants.
- Gérer les écritures système partielles sans considérer une écriture incomplète comme réussie.

## Jour 4 — Tests de régression
- Ajouter des tests négatifs ciblés sur les corruptions et incohérences.
- Exécuter les tests mémoire, worker, file, registres et suite complète.
- Vérifier que les permissions et le mode worker désactivé restent inchangés.

## Jour 5 — Documentation et transfert
- Documenter le contrat du journal, les limites et la procédure de récupération.
- Exécuter les contrôles et CI sur le SHA final.
- Ouvrir une PR brouillon non fusionnée.

## Critères d'acceptation
- Tous les événements sont validés avant consommation.
- Aucun ID mémoire dupliqué ou archivage invalide n'est accepté.
- Les événements sensibles ou malformés sont rejetés.
- Tests et CI réussissent sur le SHA exact de tête.
- Aucun déploiement, migration distante, activation ou effet externe.
