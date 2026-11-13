# PAPI AI WORKERS — évaluation de rentabilité

## Mission 19 — Jour 4/5

Le module `papi_core.profitability` estime la rentabilité unitaire d'une mission ou d'un service proposé par un agent.

### Données requises

- `currency` : code ISO 4217 (ex. `XOF`, `USD`, `EUR`).
- `gross_revenue` : revenu brut estimé.
- `platform_fee` et `payout_fee` : commissions et frais de retrait/paiement.
- `infrastructure_cost` et `other_cost` : coûts opérationnels.
- `estimated_hours` : temps de travail estimé, strictement positif.
- `target_hourly_rate` : valorisation du temps de travail.
- `minimum_margin_percent` : seuil facultatif, par défaut zéro.

Tous les montants doivent être exprimés dans la même devise. Aucun taux de change n'est inventé ni appliqué.

### Calculs

- Net de trésorerie avant travail = revenu brut − frais − coûts opérationnels.
- Coût du travail estimé = heures × taux horaire cible.
- Bénéfice net estimé = net avant travail − coût du travail.
- Taux horaire net et marge nette sont calculés à partir de ces valeurs.

### États

- `viable_for_human_review` : seuils estimés atteints, revue humaine obligatoire.
- `below_minimum_margin` : marge sous le seuil demandé.
- `below_hourly_target` : rendement horaire inférieur à la cible.
- `loss_making` : revenu nul ou bénéfice net estimé négatif.

Interface : `evaluate_offer_profitability(offer)` et `rank_offer_profitability(offers)`.

Les résultats sont des estimations, pas des revenus garantis. Ce module n'effectue aucun paiement, achat, investissement, conversion de devise, acceptation de contrat ou autre action externe. Toute dépense et tout engagement restent soumis à autorisation explicite.
