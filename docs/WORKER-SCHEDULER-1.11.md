# PAPI WORKER SCHEDULER 1.11

## Objectif
Construire un ordre de traitement déterministe des jobs, appliquer une priorité avec vieillissement (aging), répartir la charge sur les workers admissibles et limiter le nombre de propositions par cycle.

## Règles
- Ordre initial : urgent, high, normal, low.
- Chaque intervalle d'ancienneté configurable fait monter d'un niveau, sans dépasser urgent.
- Égalité : date d'attente la plus ancienne, puis identifiant du job.
- Admissibilité : worker actif, identité active et complète, permissions identiques entre registre worker et carte d'identité, permission du handler présente et non interdite.
- Répartition : worker au ratio charge/capacité le plus faible, puis charge, puis identifiant.
- Les jobs avec bail actif sont surveillés ; un bail expiré est signalé pour récupération, jamais repris directement par le planificateur.
- Le plan respecte execution_enabled et external_actions_enabled. Dans la politique actuelle, tous les jobs admissibles restent en attente car execution_enabled=false.

## Limites de sécurité
Ce module est strictement en lecture seule. Il ne contacte pas Supabase, ne réserve aucun job, ne crée aucun bail, ne démarre aucun processus et n'appelle aucun handler. Le résultat dispatch_candidate est une proposition de plan, pas une autorisation d'exécuter.

## Validation
Tests unitaires couvrant priorités, aging, déterminisme, équilibrage, capacité, permissions, handler inconnu, politique désactivée, dates invalides et absence de mutation des entrées.
