# PAPI CLIENT MANAGER 1.50

## Objectif
Suivre les demandes de service, réclamations, avis et indicateurs de satisfaction à partir d'instantanés locaux minimisés.

## API
`analyze_client_experience(cases, feedback, service_metrics=None, as_of=None)` :
- valide les dossiers de service et leur cycle de vie ;
- suit les dossiers ouverts et les avis non résolus ;
- calcule la note moyenne des avis notés ;
- calcule, par service, la note moyenne et le taux de réclamation ;
- isole les enregistrements rejetés avec leur catégorie et leur index.

## Données et confidentialité
Le module refuse les champs non prévus, notamment les coordonnées directes. Utiliser uniquement des références client internes pseudonymisées. Les commentaires libres peuvent contenir des informations personnelles : ils doivent être expurgés avant import. Ne pas importer de données sensibles, de données de paiement ou de secrets.

## Sécurité et limites
- Analyse locale en lecture seule : aucune prise de contact, aucun message, aucune relance automatique, aucun remboursement ou mouvement financier.
- Les dossiers et avis sont des données de suivi, pas une preuve de prestation ou de paiement.
- Contrôle humain requis pour les réclamations, les réponses publiques et toute décision commerciale.
- Budget : 0 XOF ; aucune dépendance ou API payante ajoutée.
- Tests ajoutés mais non exécutés dans cette livraison.
