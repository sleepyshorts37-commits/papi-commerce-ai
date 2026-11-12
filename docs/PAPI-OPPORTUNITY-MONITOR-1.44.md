# PAPI OPPORTUNITY MONITOR 1.44

## Objectif
Comparer deux instantanés du portefeuille, suivre les scores, repérer les fiches anciennes et documenter les paiements.

## Fonctionnement
- Classe les fiches : nouvelle, améliorée, en baisse, statut modifié ou inchangée.
- Signale les fiches anciennes (14 jours par défaut).
- Signale les fiches absentes sans les déclarer closes.
- Comptabilise un paiement seulement avec montant, référence et vérificateur.

## Garde-fous
- Comparaison locale ; aucune navigation réseau.
- Aucune candidature, prise de contact, publication, dépense, commande ou transaction.
- Budget : 0 FCFA ; exécution désactivée.
- Une référence et un vérificateur déclarés ne constituent pas une preuve bancaire indépendante.
- Les prévisions ne sont jamais assimilées à des recettes.

## Validation
Sept tests unitaires sont ajoutés. Ils ne sont pas déclarés réussis tant qu'une exécution locale ou CI n'a pas été observée.
