# PAPI OPPORTUNITY SCANNER 1.42

## Objectif et fonctionnement
Normaliser des résultats de recherche publique et produire des fiches compatibles avec le moteur de notation 1.41. Le scanner reçoit les résultats d'un outil de recherche autorisé ou d'un opérateur humain. Il n'effectue aucune recherche Internet ni requête réseau.

1. Réception : titre, URL HTTPS, extrait, date de publication et source.
2. Normalisation, validation, déduplication et rejet des entrées invalides.
3. Classement initial en pistes découvertes / à vérifier.
4. Attestation requise avant notation : accès depuis le Sénégal, paiement et retrait, frais, conditions, conformité, vérificateur identifié, date et liens de preuves publiques.
5. Transmission des seules fiches admissibles à rank_opportunities ; retour des trois meilleures pistes au maximum.

## Statuts
- discovered : résultat reçu et normalisé.
- needs_verification : une condition essentielle reste incertaine ou manque.
- verified_attested : contrôles déclarés confirmés et preuves publiques référencées.
- rejected : entrée invalide ou fiche rejetée par le moteur de notation.

**Limite :** verified_attested signifie qu'un vérificateur a fourni une attestation structurée. Le module ne visite pas les URL, n'authentifie pas les documents et ne confirme pas lui-même le contenu des pages. Un contrôle humain des conditions réelles applicables aux résidents du Sénégal reste obligatoire.

## Données
Chaque résultat accepte title, url, snippet, published_at, source_name, opportunity_id, verification et scoring.
verification contient exactement : senegal_access, payment_and_withdrawal, fees, terms, legal_compliance (tous à confirmed), reviewer, reviewed_at et evidence_urls.
scoring contient les critères et estimations attendus par score_opportunity 1.41.

## Garde-fous
- Budget 0 FCFA ; aucune dépense ou souscription.
- Aucun scraping, contact, inscription, publication, commande, publicité ou transaction.
- Aucun pari sportif ni trading spéculatif.
- Aucune donnée privée nécessaire ou collectée.
- Les estimations ne sont pas des ventes ; les recettes nécessitent une preuve de paiement réelle.
- Les tests unitaires sont ajoutés mais ne sont pas déclarés réussis sans exécution CI/Python.

## Fichiers
- runtime/papi_core/opportunity_scanner.py
- tests/test_opportunity_scanner.py
- docs/PAPI-OPPORTUNITY-SCANNER-1.42.md
