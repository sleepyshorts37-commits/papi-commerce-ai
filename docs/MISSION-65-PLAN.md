# Mission 65 — PAPI Agent Identity Transaction Manager

## Ordre unique d'exécution — 20 journées regroupées

Agir comme une équipe senior combinant architecture logicielle, sécurité applicative, cryptographie appliquée, ingénierie SQLite, qualité logicielle et gouvernance multi-agents. Exécuter l'intégralité des vingt journées dans une seule mission, sur une seule branche et une seule PR. Ne pas attendre une validation entre les journées : poursuivre automatiquement les étapes non sensibles et produire les livrables dans le même ordre. Les validations humaines restent obligatoires pour les transitions sensibles réelles ; cette mission ne réalise que des tests locaux et des changements de code/documentation.

## Objectif général

Construire un gestionnaire transactionnel central du cycle de vie des identités d'agents PAPI, cohérent avec le registre canonique et les mécanismes Ed25519 existants. Il doit sérialiser les transitions, empêcher les conflits de révision, rendre les requêtes idempotentes, exiger une référence d'approbation humaine, conserver un journal append-only vérifiable et refuser les états incohérents.

Le gestionnaire est un registre local de contrôle et d'audit. Il ne remplace pas data/agents.json, ne génère ni ne déplace de clé privée, ne modifie pas les permissions du système, n'active aucun agent et ne communique avec aucun service externe.

## Plan de travail — 20 jours

### Jour 1 — Inventaire du système d'identité
- Cartographier le registre canonique, les modules Ed25519, le contrôle d'accès, les workers, les signatures, les révocations et les journaux existants.
- Identifier les sources de vérité et les responsabilités de chaque composant.
- Documenter les risques de divergence.

### Jour 2 — Modèle de domaine
- Définir les états active et revoked, les révisions monotones et les versions de clés.
- Définir les opérations provision, rotation, modification des permissions et révocation.
- Interdire la réactivation implicite d'une identité révoquée.

### Jour 3 — Contrat transactionnel
- Définir les préconditions et postconditions de chaque opération.
- Définir les erreurs de conflit, d'état absent, de révision obsolète et de permission interdite.
- Exiger une référence d'approbation explicite pour toute transition.

### Jour 4 — Schéma SQLite
- Concevoir un instantané d'état courant par agent et un journal d'événements append-only.
- Ajouter les contraintes d'unicité et index nécessaires.
- Définir une initialisation idempotente compatible avec une base neuve.

### Jour 5 — Durcissement du stockage
- Protéger le répertoire et le fichier de base locale.
- Refuser les chemins symboliques pour la base.
- Configurer les timeouts SQLite sans prétendre protéger contre un administrateur local hostile.

### Jour 6 — Sérialisation des transitions
- Utiliser BEGIN IMMEDIATE pour sérialiser les écritures concurrentes.
- Faire évoluer l'état courant et ajouter l'événement dans une même transaction.
- Garantir le rollback complet en cas d'erreur.

### Jour 7 — Idempotence
- Définir une clé d'idempotence par agent et opération.
- Rejouer le résultat d'une requête strictement identique sans ajouter d'événement.
- Refuser la réutilisation de la même clé avec une requête différente.

### Jour 8 — Contrôle optimiste des révisions
- Exiger la révision attendue pour toute transition après provision.
- Incrémenter la révision exactement une fois par transition acceptée.
- Refuser les mises à jour concurrentes périmées.

### Jour 9 — Provision contrôlée
- Créer un état initial uniquement si l'identité est absente.
- Exiger la version de clé initiale 1 et des listes de permissions valides.
- Refuser les identifiants invalides, doublons et permissions contradictoires.

### Jour 10 — Rotation contrôlée
- Exiger l'identité active et la version de clé immédiatement suivante.
- Préserver les permissions existantes pendant une rotation.
- Ne jamais manipuler ni générer de clé privée dans ce gestionnaire.

### Jour 11 — Permissions
- Permettre une mise à jour explicite des permissions avec approbation.
- Préserver les interdictions existantes si aucune nouvelle liste n'est fournie.
- Refuser toute permission présente simultanément dans les listes autorisée et interdite.

### Jour 12 — Révocation terminale
- Révoquer une identité active en vidant ses permissions effectives dans l'instantané.
- Conserver l'historique d'audit.
- Refuser toute rotation ou modification ultérieure après révocation.

### Jour 13 — Journal append-only
- Protéger les événements contre UPDATE et DELETE au moyen de triggers SQLite.
- Enregistrer acteur, approbation, opération, révision, version de clé, résultat et date.
- Ne jamais inscrire de secret, clé privée, jeton ou donnée sensible.

### Jour 14 — Chaîne d'intégrité
- Chaîner chaque événement au hash du précédent.
- Utiliser une sérialisation JSON canonique et SHA-256.
- Ajouter une vérification complète de la chaîne et un diagnostic fail-closed.

### Jour 15 — Tests d'idempotence et de concurrence
- Tester les doublons exacts, les collisions de clés d'idempotence et les révisions obsolètes.
- Tester l'accès concurrent avec plusieurs connexions SQLite.
- Vérifier qu'une seule transition concurrente gagne à révision identique.

### Jour 16 — Tests de sécurité
- Tester les identifiants malformés, permissions contradictoires et références d'approbation absentes.
- Tester les tentatives de modification/suppression du journal.
- Tester les bases symboliques et les permissions du fichier.

### Jour 17 — Tests de panne et de cohérence
- Injecter des erreurs avant et pendant les écritures.
- Vérifier le rollback de l'état et de l'événement.
- Vérifier que les états courants peuvent être rapprochés des événements sans inventer de transitions.

### Jour 18 — Intégration documentaire
- Documenter le rôle du gestionnaire par rapport au registre canonique et Ed25519.
- Décrire le protocole d'approbation et le traitement des conflits.
- Documenter les limites de la chaîne hashée : elle détecte les altérations, mais ne fournit pas à elle seule une preuve inviolable contre un administrateur ayant accès à la base.

### Jour 19 — Validation et revue
- Exécuter les tests ciblés et la suite du dépôt.
- Contrôler les imports, le style, les types, les migrations et la compatibilité Python.
- Rechercher secrets, clés privées, données personnelles et appels réseau non autorisés.
- Corriger les défauts et relancer les validations.

### Jour 20 — Clôture de mission
- Mettre à jour la roadmap et le rapport final.
- Créer une PR brouillon unique, basée sur la branche de Mission 64.
- Attendre la CI sur le SHA exact de tête.
- Présenter les résultats, limites, fichiers modifiés et pourcentage d'avancement.
- Ne pas fusionner ni déployer.

## Livrables attendus

- runtime/papi_core/identity_transactions.py
- tests/test_identity_transactions.py
- docs/MISSION-65-PLAN.md — présent ordre unique sur vingt jours.
- docs/MISSION-65-REPORT.md — résultats, contrôles et limites.
- Mise à jour de docs/ROADMAP.md.

## Critères d'acceptation

1. Provision, rotation, changement de permissions et révocation transactionnels.
2. Référence d'approbation obligatoire pour toute transition.
3. Idempotence stricte et contrôle de révision.
4. Sérialisation SQLite et rollback atomique état/événement.
5. Journal append-only et chaîne SHA-256 vérifiable.
6. Révocation terminale et permissions interdites non attribuables.
7. Tests couvrant les cas nominaux, conflits, sécurité, panne et altération.
8. CI verte sur le SHA final exact.

## Gouvernance non négociable

Aucun agent réel n'est provisionné, activé ou révoqué par cette mission. Aucun compte, secret, clé privée ou permission externe n'est créé. Aucun service distant, Supabase, worker, scheduler, réseau, publication, prospection, dépense, retrait, transfert ou paiement n'est déclenché. Toute action réelle future nécessite une autorisation distincte du propriétaire. PR en brouillon, non fusionnée.
