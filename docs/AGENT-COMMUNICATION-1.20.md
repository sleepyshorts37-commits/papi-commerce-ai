# PAPI AGENT COMMUNICATION SYSTEM — Phase 1.20

## Scope
Cette phase ajoute une couche de messagerie interne documentaire pour PAPI COMMERCE AI.

## Fonctionnalités
- Enveloppes structurées : identifiant, émetteur, destinataire, type, sujet, corps, priorité, horodatage et tâche liée facultative.
- Types : `task.proposal`, `task.assignment`, `task.update`, `report`, `alert`, `question`, `answer`.
- Priorités : `low`, `normal`, `high`, `critical`.
- Vérification des identités présentes, du statut actif de l'émetteur, du profil complet et de la permission explicite `send_internal_messages`.
- Projection en lecture seule des seuls événements `agent.message.created` valides et non dupliqués.
- Refus des contenus qui semblent contenir une adresse e-mail ou un numéro de téléphone.

## Limites et sécurité
- Un candidat reste un brouillon : aucune persistance, livraison, notification, affectation de tâche ou exécution.
- La messagerie n'active aucun agent et n'accorde aucune permission.
- L'authentification cryptographique runtime et la vérification de l'approbation du propriétaire ne sont pas implémentées.
- Les profils actuels sont majoritairement planifiés/incomplets et n'ont pas la permission d'envoi ; le refus par défaut est donc attendu.
- Les événements doivent être ajoutés au journal par un mécanisme autorisé séparé ; ce module ne les écrit pas.
- Aucune donnée client, coordonnée personnelle, secret ou identifiant de compte ne doit être placé dans les messages.

## Vérification
Tests unitaires ajoutés dans `tests/test_agent_messaging.py`. Leur exécution et la CI restent à confirmer.
