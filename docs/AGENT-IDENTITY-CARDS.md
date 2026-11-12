# Cartes d'identité professionnelles des agents PAPI

## Objectif
Chaque agent doit posséder une identité numérique individuelle, unique et liée à son identifiant runtime. La carte documentaire décrit la fonction et le périmètre autorisé ; elle ne constitue pas à elle seule une preuve cryptographique et ne donne aucun droit d'exécution.

## Champs requis
- Identifiant numérique unique et identifiant runtime existant.
- Nom complet, fonction, service et responsable hiérarchique.
- Mission, compétences, objectifs mesurables.
- Niveau d'autonomie : `none`, `assisted`, `bounded` ou `supervised`.
- Permissions accordées et actions interdites.
- Statut : `planned`, `active`, `suspended` ou `revoked`.
- Date de création, historique des affectations et évaluations.
- État de complétude : `incomplete` ou `complete`.

## Règles de sécurité
1. Une carte est liée à un seul `agent_id` existant ; un agent ne peut avoir qu'une carte.
2. Les identifiants de carte sont uniques et ne doivent jamais être réattribués.
3. Une carte incomplète ne peut pas déclarer l'agent actif.
4. Un agent actif doit avoir un responsable, des compétences et des objectifs définis.
5. La carte ne peut pas augmenter les permissions runtime. Le moteur d'autorisation reste la source de décision effective.
6. Aucun agent ne reçoit de permission de retrait, transfert, paiement, dépense ou engagement juridique autonome.
7. Les historiques sont conservés ; les changements doivent ajouter une entrée plutôt qu'effacer l'ancien historique.
8. Les clés privées Ed25519 restent locales et ne sont jamais stockées dans le registre documentaire.

## Liaison de l'identité à l'authentification Ed25519
Le module `runtime/papi_core/agent_identity_auth.py` fournit un contrôle fail-closed avant l'authentification cryptographique :
- il exige une carte unique correspondant à l'agent demandeur ;
- la carte doit être `active` et `complete`, et l'entrée correspondante du registre des agents doit être active ;
- les permissions et actions interdites de la carte doivent correspondre exactement à celles du registre runtime ;
- la signature Ed25519 est ensuite vérifiée avec les contrôles de fraîcheur et de rejeu existants ;
- les clés privées ne sont ni chargées ni manipulées par ce module.

Ce contrôle est maintenant branché aux chemins d'envoi et de lecture des agents dans `runtime/papi_core/chat.py`. Il s'applique aux identifiants présents dans le registre runtime ; les principaux `owner` et `system` conservent leur voie d'authentification distincte. Le chemin du registre d'identités peut être injecté explicitement pour les tests isolés. Les cartes `planned` ou incomplètes restent refusées.

## État de l'implémentation
La version 0.7 branche la vérification des cartes sur les opérations PAPI CHAT. La suite de 173 tests, y compris les tests d'intégration PostgreSQL, ainsi que les validations du registre et de la documentation, sont réussies sur le commit vérifié.

Ce travail n'active pas les 40 agents. Les informations non encore décidées (notamment responsables, objectifs et niveaux d'autonomie individuels) doivent rester explicitement incomplètes plutôt que d'être inventées. Les cartes complètes des agents seront remplies et revues avant toute activation.
