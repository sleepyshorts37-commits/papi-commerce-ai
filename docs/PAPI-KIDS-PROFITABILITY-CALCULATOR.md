# Mission 82 — Calculateur de rentabilité PAPI KIDS

## Livrable
Moteur local `runtime/papi_core/kids_profitability.py` et commande `kids-profitability`. Calcul unitaire, sans appel réseau.

## Données exigées
Chaque montant est une chaîne décimale avec devise, source et date : prix public, impression, distribution, expédition supportée par l'éditeur, taxes, retenues, frais fixes par exemplaire, coût initial. Les taux de commission et de paiement exigent aussi une source et une date. Tous les montants partagent une devise. Hors XOF, la conversion vers XOF exige un taux, une source et une date. Coûts absents, null, nombres flottants, montants négatifs, dates impossibles et devises incohérentes sont rejetés.

## Calculs
Commission = prix × taux de commission. Frais de paiement = prix × taux de paiement. Net unitaire = prix − commission − frais de paiement − impression − distribution − expédition − taxes − retenues − frais fixes. Prix de seuil = coûts unitaires ÷ (1 − taux de commission − taux de paiement), si le dénominateur est positif. Calculs Decimal, affichage à deux décimales.

## Porte zéro avance
Le canal est comparable uniquement si son statut vaut exactement `ELIGIBLE_ZERO_UPFRONT`, le coût initial est nul et le vendeur ne finance pas la commande avant le versement. HOLD et BLOCKED ne sont jamais recommandés. Un bénéfice calculé n'autorise aucune publication.

## Utilisation
`PYTHONPATH=runtime python -m papi_core kids-profitability chemin/vers/offre.json`

Aucun tarif de plateforme n'est prérempli. Les fixtures de tests sont synthétiques et ne représentent pas des prix de marché.

## Limites
Estimateur unitaire, pas un avis fiscal/comptable. Vérifier taxes, contrats, territoires, frais de conversion, seuils et délais de versement. L'éligibilité doit venir du moteur de routage et de preuves officielles récentes.
