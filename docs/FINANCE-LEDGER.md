# Finances, paiements et comptabilité

## Périmètre actuel
Le module est un registre local append-only en XOF. Il sait valider et rapporter les écritures de recettes, dépenses, remboursements et frais. Il ne se connecte à aucun prestataire, compte bancaire, portefeuille mobile ou API de paiement.

## Reconnaissance des recettes
- Une recette est reconnue uniquement si son statut est verified et si une preuve issue d'une source autorisée est référencée.
- Une demande de paiement, facture, promesse, panier, vente déclarée ou transaction en attente n'est pas une recette encaissée.
- La preuve doit être vérifiée par le propriétaire ou une personne explicitement habilitée, à partir du relevé/portail officiel du prestataire.
- Ne jamais stocker numéro de compte, carte, téléphone privé, OTP, PIN, CVV, token, identifiant de connexion ou relevé complet dans le dépôt public. Seule une référence non sensible à la preuve est admise.

## Dépenses et remboursements
- Une dépense/frais ne peut être marqué approved ou paid sans approbation tracée.
- Une dépense paid exige une référence de preuve de paiement.
- Un remboursement doit référencer l'écriture d'origine et ne réduit les recettes que lorsqu'il est vérifié.
- Aucun transfert, retrait, achat, remboursement ou paiement n'est déclenché par ce module.

## Registre
Les écritures sont stockées dans `data/finance/entries.jsonl`, une par ligne, en ajout uniquement. Le manifeste `data/finance-ledger.json` décrit la devise et la politique, mais le journal JSONL est la source des écritures. L'ajout est conçu pour un seul écrivain local ; pas de verrou multi-processus ni de réplication distante. Sauvegardes et rapprochements périodiques restent à mettre en place.

## Commandes
- `PYTHONPATH=runtime python -m papi_core finance-validate`
- `PYTHONPATH=runtime python -m papi_core finance-report`

Le registre initial est vide. Le solde calculé est un flux net comptable des seules écritures vérifiées/payées, pas un solde bancaire temps réel.
