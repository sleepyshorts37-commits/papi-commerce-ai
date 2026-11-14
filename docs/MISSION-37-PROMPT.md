# Mission 37 — Fiabilisation de PAPI CHAT

## Objectif
Rendre le journal local PAPI CHAT strictement vérifiable avant consommation, et rendre l'écriture append-only robuste aux écritures système partielles.

## Jour 1 — Audit
- Revoir le contrat des messages et les usages du journal.
- Identifier les entrées malformées, les doublons, les dates ambiguës et les limites de stockage.
- Préserver le caractère local et non connecté de PAPI CHAT.

## Jour 2 — Validation
- Exiger une structure exacte et des types de champs stricts.
- Exiger un identifiant MSG- suivi d'un UUID hexadécimal valide.
- Exiger une date ISO-8601 avec fuseau horaire.
- Rejeter les expéditeurs/destinataires inconnus, types invalides et contenus ressemblant à des secrets.

## Jour 3 — Intégrité du journal
- Refuser les identifiants de message dupliqués.
- Refuser les lignes vides et les entrées JSON invalides.
- Compléter les écritures système partielles.
- Préserver l'historique append-only sans réparation silencieuse.

## Jour 4 — Tests
- Ajouter des tests négatifs et un test d'écriture partielle.
- Exécuter les tests PAPI CHAT, mémoire, worker, sécurité et suite complète.
- Vérifier que les actions externes et l'exécution des agents restent désactivées.

## Jour 5 — Documentation et livraison
- Mettre à jour le contrat et les procédures opérateur.
- Vérifier les deux jobs CI sur le SHA final exact.
- Ouvrir une PR brouillon, sans fusion.

## Critères d'acceptation
- Tous les messages sont validés avant lecture.
- Les IDs et horodatages sont non ambigus.
- Les doublons, lignes vides et messages malformés sont rejetés.
- Les écritures partielles sont correctement poursuivies.
- Les tests et CI réussissent sur le SHA final.
- Aucun service externe n'est connecté ou activé.
