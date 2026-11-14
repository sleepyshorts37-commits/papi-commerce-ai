# Mission 25 — Approbations humaines à portée limitée

## Objectif
Renforcer la gouvernance des actions sensibles en remplaçant les simples indicateurs d'approbation par des attestations explicites, liées à une tâche et à une action précises, avec expiration et protection contre le rejeu. Cette mission prépare les contrôles ; elle ne connecte aucun canal externe.

## Jour 1/5 — Modèle de menace et contrat d'approbation
- Distinguer demande, approbation, autorisation et exécution.
- Définir les champs obligatoires : identifiant d'approbation, tâche, handler, classe d'action, décision, propriétaire, horodatages.
- Interdire qu'un agent, un payload de job ou une simple valeur `approval_status` puisse constituer une preuve d'approbation.
- Documenter la frontière de confiance de la couche d'authentification.

## Jour 2/5 — Validation stricte et portée minimale
- Ajouter un validateur Python pur et déterministe.
- Lier l'approbation à une tâche, un handler et une classe d'action exacts.
- Exiger le statut `in_progress`, le propriétaire configuré et une décision positive.
- Refuser les objets incomplets, identités non conformes et horodatages sans fuseau.

## Jour 3/5 — Expiration et anti-rejeu
- Limiter la durée de validité configurable (15 minutes par défaut, maximum 24 heures).
- Rejeter les approbations expirées, datées dans le futur ou trop longues.
- Rejeter les identifiants déjà consommés.
- Documenter qu'une garantie anti-rejeu concurrente exige une consommation atomique dans un stockage durable.

## Jour 4/5 — Audit et intégration contrôlée
- Définir les événements d'audit minimaux sans payload, secret ni donnée client.
- Définir la procédure de consommation atomique et d'escalade en cas d'échec.
- Garder les handlers externes, financiers et juridiques désactivés par défaut.
- Ne pas prétendre que le validateur réalise l'authentification ou l'exécution.

## Jour 5/5 — Tests adversariaux et clôture
- Tester identité, portée, expiration, horodatages, statut de tâche et rejeu.
- Vérifier que le module n'effectue aucune écriture, requête réseau ou action métier.
- Exécuter la suite Python via CI sur le SHA exact.
- Produire le rapport de clôture et les limites résiduelles.

## Garde-fous
- Aucun merge, déploiement ou activation de worker.
- Aucun email, DM, publication, commande, paiement, retrait ou transfert.
- Aucune dépense, abonnement, crédit API ou accès à un service hébergé.
- Aucun secret ou donnée personnelle dans le dépôt ou les tests.
- L'approbation doit provenir d'une interface authentifiée du propriétaire ; le validateur seul ne prouve pas l'identité.
- La consommation anti-rejeu en production devra être atomique et durable ; une liste mémoire ne suffit pas.
