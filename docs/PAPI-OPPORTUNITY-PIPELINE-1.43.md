# PAPI OPPORTUNITY PIPELINE 1.43

## Objectif
Relier les modules 1.42 (normalisation et attestation) et 1.41 (notation) dans un flux unique de réception, qualification et préparation de revue humaine.

## Fonctionnement
1. Reçoit jusqu'à 200 résultats fournis par un moteur de recherche autorisé ou un opérateur humain.
2. Normalise les URL HTTPS, supprime les doublons d'URL et rejette les entrées invalides.
3. Contrôle l'unicité des identifiants d'opportunité dans le lot.
4. Transmet uniquement les fiches dont les attestations structurées sont complètes au moteur de notation.
5. Prépare une file de revue humaine contenant au maximum les trois meilleures opportunités classées « test » ou « investigate ».
6. Produit un bilan chiffré des résultats reçus, normalisés, rejetés, en attente et admissibles à la revue.

## Signification des décisions
- test : candidat à examiner par un humain avant toute expérimentation ; ce n'est pas une autorisation.
- investigate : recherche et vérification humaines complémentaires nécessaires.
- hold : opportunité bloquée ou insuffisamment attractive.
- reject : opportunité rejetée par les règles de notation ou de conformité.

## Garde-fous
- Aucune recherche réseau ou navigation web intégrée.
- Aucun message, e-mail, appel, inscription, publication, commande ou contrat.
- Aucune dépense, souscription, opération financière ou retrait.
- Budget de référence : 0 FCFA.
- Toute expérimentation nécessite une validation humaine préalable.
- Les attestations fournies ne sont pas authentifiées indépendamment.
- Aucune estimation ne doit être comptabilisée comme vente ou revenu.
- Seuls les paiements réellement vérifiés via une source autorisée peuvent être reconnus comme recettes.

## Fichiers
- runtime/papi_core/opportunity_pipeline.py
- tests/test_opportunity_pipeline.py

## État de validation
Les tests sont écrits mais ne sont pas déclarés réussis tant qu'une exécution CI ou locale n'a pas été observée.
