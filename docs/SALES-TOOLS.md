# Outils commerciaux PAPI

## Périmètre
Le registre local organise prospects, opportunités, offres, pipeline et interactions, notamment pour PAPI DIGITALISATION & IA (audit, conseil, intégration, formation et support B2B). Il ne prospecte pas, ne contacte personne, ne publie rien et ne crée aucune commande.

## Données
- Prospect : identifiant interne, nom professionnel, source publique vérifiable, segment, pays, statut, priorité, dernière vérification, opposition et notes non sensibles.
- Opportunité : activité PAPI, besoin observé, valeur et coût estimés en XOF, risque, délai, confiance et statut.
- Offre : référence, activité, prix, coût direct, disponibilité, source fournisseur et conditions. Marge indicative = prix moins coût direct.
- Pipeline : prospect et offre référencés, étape, montant, probabilité et prochaine action.
- Interaction : note interne ou brouillon. Une action externe exige une approbation explicite et une preuve avant d'être marquée envoyée.

## Protection et gouvernance
- Utiliser uniquement des informations professionnelles publiques et nécessaires. Le dépôt étant public, ne jamais inscrire de données clients, coordonnées privées, conversations ou secrets.
- Un refus doit être enregistré avec opt_out=true et statut opted_out, puis respecté.
- Aucun email, DM, appel, publication, commande ou contrat n'est déclenché par ce module.
- Toute communication externe exige l'approbation explicite du propriétaire au moment de l'action.
- Aucun prix, marge, opportunité ou prospect ne constitue un revenu. Le revenu n'est comptabilisé qu'après vérification indépendante du paiement dans le futur module financier.

## Utilisation
PYTHONPATH=runtime python -m papi_core sales-validate
PYTHONPATH=runtime python -m papi_core sales-report

Le rapport est local et en lecture seule. Le registre initial est vide. Les exemples éventuels doivent être fictifs.


## Offres PAPI DIGITALISATION & IA

Une offre peut référencer séparément l'audit, le conseil, la conception, l'intégration, le déploiement par employé, la formation et le support récurrent. Les licences et coûts de fournisseurs tiers doivent être isolés des honoraires PAPI. Un devis doit préciser le périmètre, les exclusions, les jalons, les coûts récurrents, les critères d'acceptation et les responsabilités du client. Les tarifs ne sont pas prédéfinis : ils doivent être calculés à partir du coût direct, du temps de travail, du risque et de la valeur livrée, puis approuvés.

Les prestations de santé exigent un examen renforcé des données et des limites d'usage. Aucune IA ne doit diagnostiquer, prescrire ou décider de la délivrance d'un médicament.
