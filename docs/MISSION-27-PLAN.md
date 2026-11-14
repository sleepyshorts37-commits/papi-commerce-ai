# Mission 27 — PAPI OUTBOX : exécution fiable et idempotente

## Objectif
Créer une file transactionnelle d'intentions métier, distincte de la file de jobs actuelle. Le producteur enregistre l'intention dans la même transaction que le changement métier. Les workers réclament un événement avec un bail et un jeton de fencing. La même clé d'idempotence ne crée jamais deux événements.

## Jour 1/5 — Contrat d'architecture et modèle de menace
- Définir l'outbox comme journal durable d'intentions, sans effet externe dans PostgreSQL.
- Distinguer événement métier, tentative de livraison, job de worker et preuve d'effet chez le prestataire.
- Définir les statuts, clés d'idempotence, tentatives, baux et événements d'audit.
- Documenter les cas de crash avant/après livraison et la limite exactly-once.

## Jour 2/5 — Persistance transactionnelle et déduplication producteur
- Ajouter les tables outbox et tentatives.
- Ajouter une fonction d'insertion idempotente : même clé + même contenu renvoie le même ID ; même clé + contenu différent est refusé.
- Définir le contrat producteur : mutation métier et insertion outbox doivent être dans une seule transaction PostgreSQL.
- Rejeter les payloads non objets, trop volumineux ou contenant des secrets/données personnelles (les producteurs ne transmettent que des références minimales).

## Jour 3/5 — Claim, bail, fencing et retries
- Ajouter le claim concurrent avec FOR UPDATE SKIP LOCKED.
- Utiliser un lease_token unique et une durée bornée.
- Réclamer les baux expirés avec un nouveau jeton.
- Ajouter ack, retry exponentiel borné et dead-letter.
- Écrire chaque transition dans un journal de tentatives append-only.

## Jour 4/5 — Idempotence aval et résilience
- Définir une clé stable propagée au prestataire pour les API qui prennent en charge l'idempotence.
- Documenter les résultats ambigus (timeout après acceptation fournisseur) et la réconciliation.
- Exiger une outbox/inbox ou un registre d'effet aval pour les consommateurs internes.
- Tester appels concurrents, crash simulé, rejeu, mauvais bail, tentatives maximales et historique d'audit.
- Ne jamais prétendre à l'exactly-once pour un système externe sans coopération du prestataire.

## Jour 5/5 — CI, sécurité et clôture
- Exécuter tests PostgreSQL, test concurrent multi-session et PostgREST local.
- Vérifier RLS, privilèges, index et rollback protégé.
- Documenter la procédure de reprise et la limite des effets externes.
- Produire le rapport de clôture avec résultats CI sur le SHA exact.

## Garde-fous
- Aucun worker permanent ni ordonnanceur activé.
- Aucun appel email, WhatsApp, réseaux sociaux, paiement, transfert ou prestataire.
- Aucun projet Supabase hébergé, secret, abonnement ou dépense.
- Aucun merge ni déploiement sans autorisation.
- Les payloads contiennent des références techniques minimales, jamais des secrets ou données client.
- L'outbox enregistre une intention ; la livraison réelle reste désactivée.
