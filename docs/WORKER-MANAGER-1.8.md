# PAPI WORKER MANAGER 1.8

## Fonction
Le Worker Manager prépare un plan de cycle à partir des jobs, workers, identités, handlers autorisés et de la politique centrale.

## Décisions
- `monitor` : un job possède encore un bail valide.
- `ignore` : statut non réservable.
- `block` : handler absent ou aucun worker qualifié.
- `hold` : worker éligible mais exécution désactivée.
- `candidate` : prérequis déclaratifs réunis ; cela ne constitue pas un lancement.

## Contrôles
Identité active et complète, statut worker actif, permission déclarée à la fois sur le worker et sa carte d'identité, absence d'interdiction, handler explicitement enregistré. Une action externe nécessite en plus `external_actions_enabled=true`.

## Limites
Cette version est un planificateur pur et déterministe. Elle ne lit pas la file distante, ne réserve aucun job, ne renouvelle aucun bail, ne démarre aucun processus et n'exécute aucun handler. L'intégration à la file Supabase et l'authentification cryptographique des workers restent des étapes séparées. La politique actuelle garde l'exécution désactivée.
