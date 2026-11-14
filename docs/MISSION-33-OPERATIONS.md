# Mission 33 — Contrat d'exploitation et gates de synchronisation

## Invariants
- Un plan est une proposition, pas une commande.
- Le plan contient des identifiants, types, opérations, digest et statut ; jamais le contenu mémoire ou chat.
- Les conflits bloquent toute exécution et exigent un arbitrage humain documenté.
- Les actions locales/distantes ne sont exécutables qu'après approbation vérifiée par un backend de confiance, liée au digest exact et à une destination précise.
- L'agent qui produit le plan ne peut pas s'approuver lui-même.
- Un snapshot incomplet, une identité invalide ou un résultat réseau incertain bloque la suite.

## États cibles d'une future exécution
`proposed → approved → applying → completed`
Branches de sortie : `blocked`, `partial`, `expired`. Une transition vers `applying` doit exiger une approbation authentifiée et un lease atomique. Ces états sont des contrats documentaires, pas une machine active livrée ici.

## Idempotence et reprise
Chaque action doit conserver un identifiant immuable dérivé de plan + agent + destination + opération + ressource. Le backend futur doit enregistrer la clé d'idempotence et l'état d'effet dans la même transaction que le changement local lorsqu'il est possible. En cas de timeout après envoi, lire l'état distant avant tout retry. Ne jamais conclure à l'échec d'un effet uniquement parce que la réponse réseau manque.

## Observabilité sans contenu
Journaliser correlation ID, plan digest, action ID, instance, type d'opération, durée, résultat catégorisé et compteur de retry. Ne pas journaliser corps de message, titre/contenu mémoire, credentials, URL avec paramètres sensibles ou payload complet.

## Gates avant production
1. Identité propriétaire cryptographiquement vérifiée.
2. Approbation humaine authentifiée liée au digest exact.
3. Projet de test et droits effectifs vérifiés.
4. Tests multi-instances et concurrence réussis.
5. Sauvegarde et restauration démontrées.
6. Revue indépendante et plan de rollback approuvés.
7. Autorisation distincte de mise en service.

Aucun de ces gates n'est implicitement validé par la présence du planificateur.
