# PAPI REVENUE OPTIMIZATION — Phase 1.31

## Objectif
Comparer les économies unitaires des offres, commissions, seuils de rentabilité et scénarios de prix à partir de données explicitement fournies. Le moteur est strictement en lecture seule.

## Entrées
Chaque offre exige un nom, une activité PAPI reconnue, un marché, la devise XOF, un prix de vente et un coût variable unitaire. Les coûts fixes sont facultatifs mais doivent préciser leur période. Les ventes observées, objectifs de ventes, commissions, scénarios de prix et références de preuve sont facultatifs.

Les commissions utilisent les points de base : 100 bps = 1 %, maximum 10 000 bps = 100 %. La commission unitaire combine la part variable et le montant fixe.

## Calculs
- Contribution unitaire = prix de vente - coût variable unitaire.
- Taux de contribution = contribution unitaire / prix de vente.
- Contribution nette de commission = contribution unitaire - commission.
- Seuil de rentabilité en unités = plafond(coûts fixes / contribution unitaire), uniquement si les coûts fixes sont connus et la contribution positive.
- Chiffre d'affaires cible = prix × quantité cible ; contribution cible = contribution nette × quantité cible - coûts fixes lorsque fournis.
- Scénarios de prix alternatifs : comparaison arithmétique, sans modification automatique du prix.

## Réalisé versus cible
Un nombre de ventes fourni seul n'est pas une preuve de paiement et ne crée aucun chiffre d'affaires réalisé. Les champs de recettes réelles ne sont acceptés que si `payment_verification_status` vaut `verified` et si les unités et le montant payé vérifiés sont fournis. Le moteur ne vérifie pas lui-même les relevés du prestataire de paiement : l'étiquette signifie que la source de données affirme avoir effectué cette réconciliation.

Les objectifs sont des scénarios hypothétiques de planification, jamais des prévisions.

## Limites et garde-fous
- Devise XOF uniquement ; aucun renseignement nominatif ou identifiant de transaction n'est requis.
- Taxes, retours, frais de paiement et coûts non fournis sont exclus.
- Coûts manquants : aucune marge ou rentabilité artificiellement complétée.
- Aucun changement de prix, paiement de commission, transaction, achat, dépense ou action externe.
- Aucun agent ni worker n'est activé.

## Command Center
Le paramètre facultatif `revenue_observations` alimente la section `revenue_optimization`. Une liste vide est utilisée par défaut.
