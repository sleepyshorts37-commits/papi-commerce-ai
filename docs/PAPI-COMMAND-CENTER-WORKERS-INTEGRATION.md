# PAPI COMMAND CENTER — intégration de PAPI AI WORKERS

## Mission 20 — Jour 1/5

### Objectif
Rendre le rapport PAPI AI WORKERS visible dans la sortie consolidée de PAPI COMMAND CENTER, sans démarrer de worker, sans synchronisation implicite et sans action externe.

### Contrat
`build_command_center` accepte trois collections facultatives :
- `platform_candidates` : candidats issus du module de découverte ;
- `handoffs` : dossiers nécessitant une intervention humaine ;
- `profitability_results` : résultats d'évaluation économique.

Les collections sont transmises explicitement par l'appelant et traitées par `build_workers_report`. En l'absence de données, le tableau de bord expose un rapport vide, avec les garde-fous habituels.

### Garanties
- Mode `read_only_local`.
- Aucun chargement réseau, accès à Supabase ou lecture de compte externe.
- Aucun worker ou scheduler démarré.
- Aucune notification, inscription, candidature, acceptation contractuelle, dépense ou transaction.
- Les offres et plateformes restent soumises à une revue humaine ; le rapport ne vérifie pas indépendamment les preuves ni les revenus.

### Validation
Tests couvrant le rapport vide, l'agrégation des trois domaines, le rejet des collections invalides et le maintien des contrôles d'absence d'action.

### Limite
Cette étape établit le contrat d'intégration en mémoire. La collecte automatique et la persistance partagée sont des chantiers distincts qui nécessitent leurs propres tests et autorisations.
