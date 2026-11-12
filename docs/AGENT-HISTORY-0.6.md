# PAPI TASK ENGINE 0.6 — mémoire historique des agents

## Objectif
Produire une chronologie vérifiable et des indicateurs factuels par agent à partir du journal d'audit append-only et des tâches. Cette version ne crée pas un second journal et ne modifie ni les cartes d'identité ni les événements sources.

## Fonctionnement
`papi_core.agent_history.summarize_agent_history(agent_id, events, tasks, as_of=None)` :
- valide chaque événement avec le schéma central `papi_core.audit.validate_event` ;
- rejette les identifiants d'événement dupliqués et les dates sans fuseau ;
- trie les événements par date puis identifiant pour un résultat déterministe ;
- attribue les affectations à l'agent explicitement désigné par `details.new_assignee` ;
- attribue les transitions à l'acteur enregistré dans l'événement ;
- calcule les durées uniquement lorsque la date de création de la tâche est disponible et valide ;
- expose les échantillons utilisés, sans inventer les données manquantes.

## Indicateurs disponibles
Affectations reçues, tâches terminées/bloquées/annulées par l'agent comme acteur, transitions d'état, durée moyenne de clôture lorsque calculable, nombre d'événements retenus et chronologie minimale.

## Intégrité et limites
- Analyse strictement en lecture seule ; aucune écriture, notification, réaffectation ou activation d'agent.
- Pas de score subjectif ni de classement automatique des personnes.
- Une affectation historique est attribuée au destinataire indiqué dans l'événement d'affectation.
- Une transition est attribuée à son acteur ; cela ne prouve pas à lui seul que cet acteur est propriétaire de la tâche.
- Les durées sont calculées entre `created_at` et l'événement `done`, pas entre affectation et clôture.
- Les évaluations humaines restent dans `evaluation_history` et ne sont pas générées par ce module.
- Les données d'entrée sont fournies par l'appelant ; cette version ne lit pas directement Supabase.

## Activation
Les 40 cartes existantes restent planifiées/incomplètes. Aucun agent n'est activé par cette version. Des indicateurs réels ne seront disponibles qu'après génération d'événements d'audit réels.
