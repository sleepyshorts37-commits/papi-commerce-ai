# PAPI SALES DASHBOARD 1.49

## Objectif
Consolider les indicateurs du pipeline commercial et, facultativement, les opérations PAPI SERVICES dans un tableau de bord calculé localement.

## API
`build_sales_dashboard(sales_pipeline, services_overview=None)` consomme les résultats déjà calculés par le moteur commercial 1.48 et, en option, l'analyse PAPI SERVICES MVP. Elle restitue :
- prospects valides, rejets, répartition par statut et taux de gain ;
- relances en retard, à effectuer et prospects sans mise à jour depuis sept jours ;
- priorités commerciales triées par niveau ;
- demandes, devis, prestations livrées/en cours et indicateurs de paiements si l'instantané de services est fourni.

## Limites financières
Les ventes gagnées et le taux de conversion sont des indicateurs CRM, pas des preuves d'encaissement. Le champ de revenu reconnu fourni par PAPI SERVICES doit faire l'objet d'un contrôle indépendant auprès du prestataire de paiement. Une attestation présente dans un instantané ne constitue pas, à elle seule, une authentification technique.

## Sécurité
- Agrégation locale, sans accès réseau et sans modification des instantanés source.
- Aucun message, contact, relance automatique, publication ou transaction.
- Aucun budget ni service payant : 0 XOF.
- Les décisions et actions commerciales restent soumises à validation humaine.
- Tests ajoutés mais non exécutés dans cette livraison.
