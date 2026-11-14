# Mission 38 — Rapport de cadrage du contrat de synchronisation

## Résultat
Contrat de préparation documenté pour la synchronisation PAPI CHAT et mémoire entre instances. Cette branche apporte un format conceptuel de paquet, les invariants de sécurité, une politique d'idempotence/conflit et les exigences opérateur et tests.

## Livrables
- `docs/CHAT-MEMORY-SYNC-CONTRACT.md` — enveloppe, digest, approbation, invariants et scénarios de tests.
- `docs/MISSION-38-PROMPT.md` — prompt détaillé et critères d'acceptation en cinq jours.
- `docs/MISSION-38-PLAN.md` — plan de travail.
- `docs/MISSION-38-OPERATIONS.md` — précautions, limites et réponse à incident.

## Point de transparence
La synchronisation réelle multi-instance n'est pas implémentée dans cette étape documentaire. Le format n'est pas encore canonisé par du code, et aucun transport, adaptateur d'import, verrouillage distribué ou test d'intégration multi-instance n'est livré. La case roadmap « Synchroniser mémoire et messages entre instances » reste donc non cochée.

## Sécurité
Aucune donnée réelle n'a été exportée/importée. Aucun projet Supabase distant, migration, déploiement, worker, scheduler, communication externe ou opération financière n'a été activé.

## Validation
À compléter après exécution de la suite de tests et vérification CI sur le SHA final de la PR.

## Pull request
Brouillon, non fusionné.
