# Mission 23 — Jour 4 : crash/retry et idempotence

## Réalisations
- Ajout d'un contrat PostgreSQL jetable simulant la disparition d'un worker après réservation.
- Vérification de la récupération après expiration du bail avec incrément du compteur de tentatives.
- Vérification qu'une clé d'idempotence ne peut créer deux jobs, même si le producteur répète l'insertion avec un nouvel identifiant de job.
- Vérification du plafond `max_attempts`, du statut terminal `failed` et du refus d'une nouvelle réservation après épuisement.
- Intégration au workflow CI principal.

## Limites et garde-fous
- Le test démontre l'unicité de création et la reprise de la file ; il ne prétend pas fournir une transaction exactement-une-fois pour un système externe.
- Aucun handler métier, message, paiement, transfert ou autre effet externe n'est exécuté.
- Base PostgreSQL jetable uniquement ; aucun projet hébergé modifié.
- PR en brouillon ; aucun merge ni déploiement.
