# Mission 104 — Registre Supabase partagé des quotas

## Livrables
- Migration `013_shared_provider_quota_ledger.sql`.
- Script de retour arrière correspondant.
- Tables backend-only pour les plafonds journaliers et les réservations.
- Fonctions transactionnelles de réservation, commit, marquage d'incertitude et libération.

## Garanties de conception
- Verrou advisory transactionnel sur la clé d'idempotence, puis verrou de ligne `FOR UPDATE` sur le compartiment fournisseur/compte/modèle/jour UTC.
- Le plafond est vérifié sur la somme consommée + réservée dans la même transaction que l'insertion de réservation.
- Une clé d'idempotence répétée avec la même intention retourne la réservation d'origine ; une intention différente est rejetée.
- Les résultats fournisseur ambigus passent à `uncertain` et gardent leur consommation estimée réservée.
- Une réservation incertaine ne peut pas être libérée par la fonction normale.
- RLS activée ; accès tables et exécution RPC refusés à `public`, `anon`, `authenticated`, accordés uniquement à `service_role`.

## Contrat d'intégration
- Le backend doit fournir un identifiant de compte opaque, jamais un jeton secret.
- Le jour est calculé en UTC côté base par défaut.
- Le plafond quotidien doit être configuré depuis une source confirmée et cohérente pour le même compartiment.
- Le coût modèle doit être validé par les informations officielles du fournisseur avant usage.
- Un ajustement après mesure réelle est accepté uniquement si le total réel reste sous le plafond ; sinon la réservation reste bloquée pour rapprochement manuel.

## Limites / sécurité
- Migration non appliquée à un projet Supabase hébergé.
- Aucun secret, identifiant de projet ou compte fournisseur ajouté.
- Pas d'intégration Python Supabase ni d'activation de l'adaptateur Cloudflare dans cette mission.
- Les tests nécessitent PostgreSQL local 16 / Docker ; aucun résultat de test ne doit être supposé.
- Les réservations `uncertain` nécessitent un processus de rapprochement humain ou fournisseur avant toute libération.

## Vérifications restantes
- Appliquer deux fois la migration sur le PostgreSQL local jetable.
- Vérifier concurrence multi-session, idempotence, dépassement de quota, commit, release, et incertitude.
- Exécuter les advisors Supabase sur un environnement autorisé avant déploiement.
