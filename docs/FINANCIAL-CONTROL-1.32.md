# PAPI FINANCIAL CONTROL — Phase 1.32

## Objectif
Fournir un tableau de trésorerie en lecture seule : recettes et dépenses déclarées/vérifiées, commissions versées, mouvements par compte, catégorie et mois, soldes calculés et rapprochement avec les soldes communiqués par les prestataires.

## Entrées
Chaque écriture agrégée contient une référence interne non nominative, un compte (par exemple Wave, Orange Money, caisse ou banque), une direction (inflow/outflow), une catégorie, un montant entier XOF, un statut, une date ISO 8601 avec fuseau et un moyen de paiement. Une activité PAPI et une note non personnelle sont facultatives.

Statuts acceptés : `verified`, `declared`, `pending`. Les références doivent être uniques par compte. Les soldes d'ouverture et soldes prestataires sont des instantanés facultatifs par compte.

Aucun nom de client, téléphone, e-mail, numéro de compte, identifiant de transaction, numéro de carte, secret ou justificatif contenant des données personnelles ne doit être fourni.

## Règles de calcul
- Seules les entrées `verified` sont intégrées au mouvement de trésorerie et au solde calculé.
- Les entrées déclarées ou en attente sont affichées séparément et ne gonflent jamais la trésorerie vérifiée.
- Solde calculé = solde d'ouverture + entrées vérifiées - sorties vérifiées.
- Écart de rapprochement = solde calculé - solde communiqué par le prestataire.
- Les commissions versées sont isolées via la catégorie `commission_payout`. Les commissions gagnées ne sont pas inventées.

## Catégories
Ventes, prestations, commissions d'affiliation/partenaires, charges opérationnelles, achats de produits, livraisons, remboursements, frais de paiement, taxes, apports/retraits du propriétaire, paiements de commissions et autres.

## Command Center
Le paramètre facultatif `financial_entries` alimente la section `financial_control`. `financial_opening_balances` et `financial_provider_balances` permettent de comparer les soldes fournis. Les listes sont vides par défaut.

## Sécurité et limites
- Les statuts vérifiés sont des affirmations des données fournies ; aucun prestataire n'est interrogé et aucun relevé n'est authentifié par ce moteur.
- Le module ne constitue pas une comptabilité auditée, un bilan complet ou un conseil fiscal.
- Aucun paiement, transfert, retrait, remboursement, écriture persistante ou dépense n'est effectué.
- Les fonds restent sous contrôle exclusif du propriétaire ; les agents ne reçoivent aucune autorisation financière.

## Vérification
Tests ajoutés dans `tests/test_financial_control.py`, non exécutés dans cet environnement. CI à vérifier sur la PR.
