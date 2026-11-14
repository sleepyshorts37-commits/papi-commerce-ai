# Prompt d'exécution — Mission 31 : PAPI SHARED COMMAND CENTER

## Rôle
Agir comme ingénieur logiciel senior PostgreSQL/Supabase, architecte de systèmes multi-agents et responsable qualité/sécurité de PAPI COMMERCE AI. Travailler dans le dépôt existant, respecter ses conventions, examiner le code réel avant toute modification et ne jamais supposer qu'une capacité est opérationnelle sans preuve.

## Objectif
Construire un centre de contrôle partagé en lecture seule qui consolide les informations opérationnelles déjà présentes dans les registres PostgreSQL de PAPI : agents/workers, heartbeats, tâches, jobs, affectations, alertes du superviseur, incidents, outbox et approbations. Le tableau de bord local reste disponible. La mission ajoute un contrat de lecture partagé ; elle ne déploie pas de serveur ni d'agent.

## Jour 1 — Audit et conception
1. Examiner les migrations 001–014, le schéma partagé, les tests SQL, la documentation du Command Center et les contrôles de sécurité.
2. Inventorier les tables, colonnes, statuts, relations, index, RLS et privilèges réels.
3. Définir un contrat JSON stable : horodatage de génération, indicateurs agrégés, listes récentes bornées.
4. Classifier les données et exclure secrets, données client, payloads, documents d'identité, clés de signature, IDs d'approbation, jetons de bail et clés d'idempotence privées.
5. Écrire les décisions d'architecture et les limites d'autonomie.

## Jour 2 — API partagée
1. Créer une migration additive numérotée 015, compatible avec les migrations existantes.
2. Ajouter une fonction PostgreSQL de lecture seule, security-invoker, accessible uniquement au rôle service_role.
3. Consolider les compteurs workers, tâches, jobs, alertes, incidents, outbox et approbations.
4. Exposer des listes récentes minimales de workers/heartbeats, jobs, affectations, alertes et incidents.
5. Valider strictement le paramètre de limite (1 à 100, valeur par défaut 20).
6. Ne créer aucun chemin de mutation, d'affectation, de claim, de transition d'incident, d'émission/consommation d'approbation ou de livraison outbox.

## Jour 3 — Tests et minimisation des données
1. Ajouter un test SQL reproductible avec données CI jetables.
2. Vérifier les agrégats, les enregistrements projetés, les horodatages et les limites.
3. Vérifier les états vides et les registres déjà peuplés par les tests antérieurs.
4. Prouver l'absence de payloads, identifiants privés et clés d'idempotence dans le JSON retourné.
5. Vérifier les droits effectifs : aucun EXECUTE pour public/anon/authenticated, EXECUTE pour service_role.
6. Ne pas supposer que la base de test est vide ; les assertions doivent tolérer les fixtures des missions précédentes.

## Jour 4 — CI et retour arrière
1. Ajouter migration 015 et test associé aux deux parcours PostgreSQL jetables du workflow GitHub Actions.
2. Vérifier l'ordre d'application après migrations 001–014.
3. Ajouter un rollback qui retire uniquement la fonction de lecture et ne supprime aucune donnée métier.
4. Exécuter les tests unitaires, les contrats SQL et l'intégration PostgREST locale.
5. Corriger chaque échec, puis relancer la CI sur le SHA final exact.

## Jour 5 — Revue et clôture
1. Relire la migration, les permissions, la fonction, le test et le workflow.
2. Vérifier qu'aucun secret, payload ou donnée personnelle n'a été ajouté.
3. Documenter le contrat, l'accès serveur, la fraîcheur, les limites et les prérequis de configuration Supabase.
4. Vérifier les résultats CI sur le SHA final, les fichiers modifiés et l'état de la PR.
5. Créer/maintenir une PR draft ouverte, non fusionnée.

## Gouvernance non négociable
- Ne pas modifier les rôles, les missions, la hiérarchie, les permissions ni les responsabilités des agents.
- Ne pas activer, suspendre ou désactiver de worker.
- Ne pas lancer d'agent, scheduler, worker permanent ou consommation de queue.
- Ne pas effectuer de migration distante, déploiement ou connexion à un projet Supabase non explicitement configuré.
- Ne pas envoyer de message, contacter un prospect/client, publier, acheter, dépenser, transférer ou retirer de fonds.
- Ne pas exposer la clé service_role au navigateur ou dans Git.
- Ne pas fusionner la PR.
- Si un contrôle ne peut être exécuté, le déclarer comme non vérifié ; ne jamais annoncer un succès supposé.

## Critères d'acceptation
- Migration 015 additive et rollback non destructif.
- Snapshot JSON borné, stable, strictement en lecture seule.
- Données sensibles exclues par construction.
- Privilèges minimaux vérifiés par tests.
- Deux parcours CI PostgreSQL incluent la migration et le test.
- CI verte sur le SHA exact de la tête de branche.
- PR draft, ouverte, non fusionnée.
