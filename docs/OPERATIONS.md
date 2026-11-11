# Exploitation PAPI — registre des tâches

## Objectif
GitHub Issues sert de registre de demandes et d'incidents. À ce stade, il ne constitue pas un moteur d'agents : une issue créée ne signifie pas qu'un agent l'a exécutée.

## Créer une demande
Dans l'onglet **Issues** du dépôt, choisir **Nouvelle tâche PAPI**. Décrire un résultat vérifiable, un responsable souhaité, une priorité, les contraintes et les critères d'acceptation.

Pour une panne, choisir **Signaler un incident**. Les journaux doivent être expurgés de tout secret et de toute donnée personnelle.

## Cycle de vie recommandé
- `statut:a-trier` : demande reçue, pas encore qualifiée.
- `statut:approuvee` : autorisation obtenue si nécessaire.
- `statut:en-cours` : travail réellement commencé par une personne ou un système identifié.
- `statut:bloquee` : dépendance ou autorisation manquante.
- `statut:a-verifier` : résultat soumis à contrôle indépendant.
- `statut:terminee` : critères d'acceptation vérifiés et preuves ajoutées.

Une issue ne doit jamais être marquée terminée sur la seule base d'une déclaration non vérifiée.

## Autorisations
Par défaut, budget autorisé : **0 FCFA**. Aucun achat, abonnement, publicité payante, retrait, transfert, envoi massif, engagement contractuel, création de compte ou accès sensible sans approbation explicite du propriétaire.

Les tâches pouvant affecter des tiers (prospection, messages, commandes, paiements, publication) exigent des intégrations réelles, le respect des règles des plateformes et les autorisations adaptées. Les workflows de ce dépôt ne réalisent pas ces actions.

## Preuves minimales
Ajouter dans l'issue : résultat concret, date, lien vers le livrable ou exécution, méthode de vérification, limites connues et éventuels coûts. Ne jamais joindre de secrets ni de données client non nécessaires.

## Commandes de gestion
- **Créer une tâche** : utiliser le formulaire Nouvelle tâche PAPI.
- **Déclarer un incident** : utiliser le formulaire Signaler un incident.
- **Bloquer** : ajouter le label `statut:bloquee` et expliquer la dépendance.
- **Demander validation** : ajouter `statut:a-verifier` et joindre les preuves.
- **Clôturer** : uniquement après vérification des critères.

## Limites actuelles
Ce registre est une première brique de coordination. Il ne fournit pas encore de mémoire persistante d'agents, de planificateur autonome, de messagerie interne, de base de données métier, de connexion aux moyens de paiement ni d'exécution continue.
