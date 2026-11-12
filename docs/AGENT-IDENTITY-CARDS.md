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
8. Une identité cryptographique Ed25519 reste séparée de la carte professionnelle : les clés privées ne sont jamais stockées dans le registre documentaire.

## État de l'implémentation
La version 0.6 introduit le validateur et le modèle JSON. Le modèle n'est pas une activation des 40 agents. Les informations non encore décidées (notamment responsables, objectifs et niveaux d'autonomie individuels) doivent rester explicitement incomplètes plutôt que d'être inventées. Les cartes complètes des agents seront remplies et revues avant toute activation.
