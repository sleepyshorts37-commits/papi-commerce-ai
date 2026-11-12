# PAPI AGENT PERFORMANCE & EVALUATION 1.18

## Objectif
Présenter des indicateurs factuels par agent à partir du journal d'audit append-only et du registre des tâches.

## Indicateurs
- Tâches attribuées et transitions de tâches réalisées par l'agent.
- Tâches terminées, bloquées ou annulées, selon les événements d'audit.
- Durée moyenne de réalisation uniquement lorsque les horodatages nécessaires existent.
- Ratio de réalisation uniquement si le nombre de tâches attribuées est connu et cohérent.

## États
- `not_evaluable` : agent non déclaré actif/déployé dans le registre.
- `insufficient_evidence` : agent déclaré actif, mais historique insuffisant.
- `measured` : événements suffisants pour présenter des métriques factuelles.

Un agent planifié n'est jamais présenté comme peu performant sur la base de données absentes. Zéro, inconnu et non mesurable restent distincts.

## Résultats commerciaux
Le chiffre d'affaires reste non mesuré. Ce module n'infère aucune recette depuis des commandes, tâches ou événements génériques ; une source de paiement vérifiée et autorisée sera nécessaire.

## Limites et sécurité
Lecture seule. Aucun score subjectif, classement, sanction, changement de statut, permission, affectation, notification, dépense ou action externe. Les recommandations sont consultatives. Les tests sont ajoutés mais leur exécution et la CI doivent être vérifiées séparément.

## État actuel du projet
Les agents du registre sont documentaires/planifiés et aucun worker n'est déployé en production. Ce module ne les active pas.
