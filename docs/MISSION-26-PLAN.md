# Mission 26 — Registre durable et consommation atomique des approbations

## Objectif
Transformer le validateur de la Mission 25 en une fondation de persistance transactionnelle : enregistrer chaque approbation, la lier à une seule tâche/action, la consommer une seule fois et inscrire l'émission/consommation dans le journal d'audit, sans exécuter l'action autorisée.

## Jour 1/5 — Modèle relationnel et menace
- Définir un registre append-oriented des approbations avec identifiant unique, tâche, handler, classe d'action, approbateur, date d'émission, expiration et état de consommation.
- Relier chaque approbation à une tâche existante.
- Refuser les portées incomplètes et les durées supérieures à 15 minutes pour le premier contrat.
- Définir les rôles DB, RLS, permissions minimales et frontière de confiance du backend authentifié.

## Jour 2/5 — Emission et consommation atomiques
- Ajouter une migration additive PostgreSQL.
- Ajouter une RPC d'émission réservée au backend de confiance.
- Ajouter une RPC de consommation par UPDATE conditionnel sur identifiant, tâche, handler, classe d'action, non-consommation et non-expiration.
- Utiliser une transaction unique pour l'état consommé et l'événement d'audit.
- Un seul appel concurrent doit réussir ; tous les autres doivent recevoir false.

## Jour 3/5 — Audit durable et intégrité
- Émettre des événements minimaux approval.issued et approval.consumed.
- Ne jamais journaliser payload, contenu client, secrets, tokens, OTP, PIN ou CVV.
- Rendre l'identifiant d'événement déterministe pour empêcher les doublons.
- Refuser la suppression ou modification directe du registre par les rôles applicatifs.

## Jour 4/5 — Concurrence et résilience
- Tester les consommations concurrentes et les appels répétés.
- Vérifier qu'une portée différente, une expiration ou un identifiant inconnu ne consomme pas l'approbation.
- Vérifier l'atomicité entre consommation et audit : toute erreur d'audit doit annuler la consommation.
- Documenter l'idempotence du traitement aval : consommer l'approbation ne prouve pas qu'un effet externe a été réalisé.

## Jour 5/5 — CI, audit et clôture
- Exécuter les tests SQL sur PostgreSQL jetable et l'intégration PostgREST locale.
- Vérifier les privilèges effectifs et les migrations.
- Documenter la procédure de rollback qui refuse de supprimer un historique.
- Publier le rapport de clôture avec limites et étapes futures.

## Garde-fous
- Aucun projet Supabase hébergé, aucune migration distante et aucun secret ajouté.
- Aucun worker permanent, scheduler ou handler activé.
- Aucun message, email, publication, commande, paiement, retrait ou transfert.
- La RPC d'émission ne prouve pas elle-même l'identité du propriétaire : elle doit être appelée uniquement après authentification fiable côté serveur.
- La consommation d'une approbation n'autorise pas à elle seule l'effet métier ; la politique d'exécution reste obligatoire.
- Aucun merge, déploiement ou dépense sans autorisation explicite.
