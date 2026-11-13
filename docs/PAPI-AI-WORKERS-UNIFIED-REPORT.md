# PAPI AI WORKERS — tableau de bord unifié

## Mission 19 — Jour 5/5

Le module `papi_core.workers_report` consolide les enregistrements déjà traités par les modules de découverte, de relais humain et de rentabilité.

### Fonction

`build_workers_report(platform_candidates=[], handoffs=[], profitability_results=[])`

### Sections du rapport

1. **Plateformes** : volume total, répartition par état et éléments nécessitant une revue.
2. **Interventions humaines** : demandes en attente, confirmations, reprises et clôtures ; liens officiels et actions demandées à l'utilisateur.
3. **Rentabilité** : répartition des résultats et offres estimées suffisamment rentables pour une revue humaine.

### Utilisation prévue

Le rapport fournit une vue consolidée pour le tableau de bord PAPI. Il peut alimenter ultérieurement une interface, une file de notifications et un stockage persistant, lorsque ces intégrations seront développées et autorisées.

### Limites actuelles

Ce module est un agrégateur en mémoire : il ne lance pas de recherche web, ne collecte pas automatiquement les données des autres modules, ne stocke rien durablement et n'envoie pas de notification. Il ne vérifie pas indépendamment les preuves ni les revenus. Les données doivent lui être fournies par l'appelant.

Aucune inscription, candidature, acceptation de contrat, dépense, opération de portefeuille ou action externe n'est exécutée. Les actions personnelles restent à la charge de l'utilisateur ; les engagements financiers nécessitent une autorisation explicite distincte.
