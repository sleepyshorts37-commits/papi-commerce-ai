# Moteur commun d'évaluation des opportunités

## Périmètre

Le moteur compare des hypothèses pour les six activités : PAPI MARKET, PAPI DROPSHIPPING, PAPI AFFILIATION, PAPI FREELANCE, PAPI SERVICES et PAPI BUSINESS PARTNERS. Il ne recherche pas de clients, ne publie pas, ne commande pas, ne signe pas et ne dépense rien.

Les entrées sont des estimations fournies par un opérateur. Le moteur ne récupère aucun prix fournisseur, tarif de livraison, commission ou délai en direct. Une estimation incomplète doit être complétée avant classement ; aucune valeur commerciale n'est inventée.

## Données évaluées

- prix de vente ou rémunération brute par unité ;
- coûts directs et livraison/exécution ;
- pourcentage de commission ;
- frais de paiement ;
- réserve estimative de remboursement ;
- coût initial ;
- avance client ;
- délai de paiement fournisseur et délai d'encaissement client ;
- délai avant première recette ;
- risque estimé et confiance dans l'hypothèse.

Toutes les sommes sont des entiers XOF. Les pourcentages doivent être finis et compris entre 0 et 100.

## Calculs

- Commission et réserve = prix × pourcentage, arrondis à l'unité XOF.
- Contribution estimée = prix − coûts directs − livraison − frais de paiement − commission − réserve.
- Contribution pondérée = contribution × confiance.
- Encaissement estimé = délai avant première recette + délai de paiement client.
- Besoin de trésorerie = coût initial + dépenses fournisseur dues avant l'encaissement, moins l'avance client disponible.
- Résultat attendu après coût initial = contribution pondérée − coût initial.
- Seuil de rentabilité = nombre d'unités nécessaire pour couvrir le coût initial, si la contribution pondérée est positive.

Le délai fournisseur est comparé au délai d'encaissement client. Si le fournisseur est payé après l'encaissement client, le coût direct n'est pas compté comme besoin de trésorerie pré-encaissement. Les frais réels, retenues, taxes, change, retours et litiges doivent être estimés séparément avant toute décision.

## Classement

Le classement est déterministe et explicable :
1. priorité 0 : besoin de trésorerie nul, risque ≤25 %, encaissement ≤14 jours ;
2. priorité 1 : besoin de trésorerie nul ;
3. priorité 2 : besoin ≤5 000 XOF, risque ≤40 %, encaissement ≤30 jours ;
4. priorité 3 : autres options viables ;
5. priorité 4 : contribution non positive, résultat attendu après coût initial négatif ou risque ≥75 %.

À priorité égale, le risque, le délai d'encaissement, le score pondéré et le résultat attendu départagent les options. Le score combine risque, rapidité, besoin de trésorerie, absence de besoin initial, marge et confiance. Ces seuils sont des règles de tri initiales, pas une garantie de succès.

Une option rejetée reçoit la recommandation reject_or_rework. Le meilleur résultat peut uniquement recevoir la recommandation owner_review_for_small_pilot : l'approbation humaine reste obligatoire.

## Adaptation aux activités

- MARKET : prix produit, achat, emballage, livraison, frais de paiement et retours.
- DROPSHIPPING : prix, coût fournisseur, livraison fournisseur, commission et décalage de règlement.
- AFFILIATION : commission attendue, coûts de contenu/acquisition, retenues et délai de validation du réseau.
- FREELANCE : prix de mission, temps/coûts de production, frais de plateforme et délai de paiement.
- SERVICES : prix du service, coûts d'exécution, livraison numérique, commissions et frais de paiement.
- BUSINESS PARTNERS : valeur apportée, commission due au partenaire, coûts de qualification et délai de validation/encaissement.

## Utilisation

Depuis la racine du dépôt :

    PYTHONPATH=runtime python -m papi_core opportunity-rank path/to/opportunities.json

Le fichier d'entrée doit être un tableau conforme à schemas/opportunity.schema.json. La sortie est un classement calculé en lecture seule. N'y placer aucune donnée client privée, aucun secret ni aucune coordonnée personnelle.

Aucun jeu de données réel n'est fourni. Aucun revenu n'est déclaré et aucune option n'est approuvée ou lancée par ce prototype.
