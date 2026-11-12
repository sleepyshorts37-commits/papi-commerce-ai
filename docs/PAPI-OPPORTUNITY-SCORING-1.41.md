# PAPI OPPORTUNITY – scoring 1.41

## Objectif
Classer les opportunités sur une échelle de 0 à 100 et faire ressortir au maximum trois pistes à examiner en priorité. Le score est une aide à la décision, pas une preuve de rentabilité.

## Barème pondéré
Chaque critère est noté de 0 à 5. Le score final est la somme des notes pondérées, ramenée sur 100.

| Critère | Poids |
|---|---:|
| Accessibilité depuis le Sénégal | 20 |
| Démarrage sans coût | 15 |
| Délai avant première recette | 15 |
| Marge nette potentielle | 15 |
| Preuves de demande | 15 |
| Faible niveau de risque | 10 |
| Adéquation aux capacités opérationnelles | 10 |
| **Total** | **100** |

## Seuils de décision
- 75–100 : `test`, uniquement si les contrôles d'accès, de légalité, de paiement et de preuve sont satisfaits.
- 55–74 : `investigate`, approfondir les informations manquantes.
- 35–54 : `hold`, mettre en attente.
- 0–34 : `reject`, écarter.

Les contrôles bloquants priment toujours sur la note : accès Sénégal non confirmé, conformité incertaine/interdite, paiement inaccessible ou informations essentielles non vérifiées empêchent le classement en test. Une activité interdite est rejetée.

## Données minimales
Chaque fiche contient un identifiant opaque, un titre, une source publique, une date de vérification, l'accessibilité pays, la conformité, l'accès au paiement, le niveau de preuve, les sept notes, les estimations de coûts/délai/marge et des notes non sensibles. Les données personnelles ne sont pas admises.

## Sortie
Le moteur renvoie le score, les critères pondérés, les blocages, la décision, les estimations explicitement marquées comme prévisions, et les trois meilleures pistes classées `test` ou `investigate`.

## Garde-fous
- Analyse locale et en lecture seule des données fournies.
- Pas de navigation web intégrée, de contact, de publication, de souscription, de commande ou de paiement.
- Pas de paris, trading spéculatif ni promesse de revenus.
- Budget initial maintenu à 0 FCFA ; toute dépense reste soumise à autorisation explicite.
- Les notes doivent être étayées par une source datée ; le moteur ne prétend pas vérifier la source indépendamment.
- Aucun test commercial ne démarre automatiquement : le propriétaire autorise séparément chaque expérimentation.

## Limites
Les scores reflètent la qualité des informations saisies. Des données fausses ou obsolètes peuvent fausser le classement. Les estimations ne sont pas des revenus réels. Les tests unitaires ajoutés doivent être exécutés dans la CI avant toute mise en production.
