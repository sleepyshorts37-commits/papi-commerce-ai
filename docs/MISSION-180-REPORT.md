# Mission 180 — Suivi du cycle de vie KDP

## Livrable
- Migration PostgreSQL 023 : historique append-only des étapes de soumission et publication manuelles.
- États : soumis manuellement, épreuve reçue, épreuve approuvée, mise en ligne déclarée par le propriétaire, refusé, action requise.
- Chaque événement est lié à la version et au hash du package autorisé, au propriétaire, à une preuve SHA-256, aux notes et à la date.
- Transitions contrôlées côté serveur ; ASIN et URL Amazon HTTPS obligatoires pour déclarer la mise en ligne.
- Tableau de bord iPhone avec chronologie et formulaire de suivi.
- Les statuts sont explicitement déclaratifs : aucune interrogation automatique d'Amazon ni vérification indépendante du référencement.

## Gouvernance
Aucun téléversement, aucune publication, aucune automatisation de compte Amazon et aucune dépense.
