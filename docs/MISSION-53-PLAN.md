# Mission 53 — Plan sur cinq jours

| Jour | Travail | Résultat |
|---|---|---|
| 1 | Audit du paquet .papisync et de la charge .papidata | Champs de liaison et limites définis |
| 2 | Implémentation du manifeste local de transfert | Métadonnées source/destination, digests et delivery ID |
| 3 | Validation stricte et contrôles de fichiers | Rejet des falsifications, liens et tailles hors limites |
| 4 | Tests de sécurité et de cohérence | Régressions automatisées |
| 5 | Documentation, roadmap, CI et revue finale | PR brouillon vérifiée sur son SHA final |

## Critères d'acceptation
Le manifeste est déterministe, vérifiable et fail-closed ; les fichiers restent intacts ; aucune opération réseau ou métier n'est déclenchée ; tous les tests et jobs CI passent sur le commit final.
