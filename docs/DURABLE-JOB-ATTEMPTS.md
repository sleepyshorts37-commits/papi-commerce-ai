# Identifiants et historique des tentatives de job

## Modèle

Chaque réservation effective réalisée par `papi_claim_job` crée un UUID `attempt_id` distinct et une ligne dans `papi_job_attempts` dans la même transaction que la mise à jour de `papi_jobs`.

Une ligne contient le job, le numéro de tentative, le worker détenteur, le jeton de bail, le statut, les dates de début/fin et le code d'erreur éventuel. Le job référence sa tentative courante par `current_attempt_id`.

## Reprise et statuts

- Une nouvelle réservation après expiration crée un nouvel UUID ; l'ancienne tentative encore `running` devient `lease_expired`.
- Une transition du job vers `done`, `retry` ou `failed` synchronise la tentative courante vers `completed`, `retry` ou `failed`.
- Une réservation expirée à la dernière tentative devient terminale et ne peut plus être reprise.
- La réservation et l'insertion de l'historique sont atomiques dans PostgreSQL ; le verrouillage `FOR UPDATE SKIP LOCKED` évite qu'une même ligne de job soit revendiquée simultanément par deux transactions.

## Compatibilité historique

La migration est additive. Les jobs existants sont conservés. Si un job ancien a déjà un compteur `attempts > 0`, la migration crée un seul instantané synthétique `is_legacy = true` correspondant au dernier état connu. Les tentatives historiques non enregistrées avant la migration ne peuvent pas être reconstruites et ne sont pas inventées.

Les jobs avec `attempts = 0` reçoivent leur premier UUID lors de leur prochaine réservation.

## Migration et retour arrière

- Migration : `infra/supabase/migrations/202611170001_durable_job_attempt_ids.up.sql`.
- Retour arrière : `infra/supabase/migrations/202611170001_durable_job_attempt_ids.down.sql`.
- Le retour arrière conserve les jobs et le compteur `attempts`, mais supprime la table `papi_job_attempts`, le lien `current_attempt_id` et l'historique UUID introduit par la migration. Sauvegarder cet historique avant un rollback si sa conservation est requise.
- La CI applique le schéma et les migrations sur un PostgreSQL jetable ; aucune migration n'est appliquée à une base de production.

Un `attempt_id` permet de corréler et dédupliquer les événements d'une tentative. Il ne garantit pas à lui seul l'exécution exactly-once d'effets externes.
