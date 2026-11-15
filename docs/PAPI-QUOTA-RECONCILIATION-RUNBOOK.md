# PAPI — Procédure de rapprochement des quotas incertains

## But
Identifier les réservations de quota Cloudflare qui restent ouvertes après un timeout, une réponse ambiguë ou un échec de commit. Le rapprochement est une opération de contrôle humain : aucun script de ce dépôt ne libère ou ne valide automatiquement une réservation incertaine.

## Outils disponibles
- `scripts/audit_shared_quota_ledger.sql` : audit SQL strictement en lecture seule.
- `scripts/test_shared_quota_concurrency.py` : exécute le contrat SQL, l'audit et les tests concurrents dans une base PostgreSQL locale uniquement.
- Tables : `papi_provider_quota_reservations` et `papi_provider_daily_quotas`.

## Classification
| Classe | Signification | Traitement |
|---|---|---|
| `ACCOUNTING_DRIFT` | Somme des réservations ouvertes différente du compteur réservé du bucket | Bloquer toute correction automatique ; investigation prioritaire |
| `LIMIT_BREACH` | Réservé + consommé dépasse la limite | Incident critique ; vérifier l'intégrité et les opérations concurrentes |
| `URGENT_RECONCILIATION` | Réservation incertaine depuis plus de 24 h | Priorité haute, rapprochement manuel |
| `RECONCILE` | Réservation incertaine depuis plus d'une heure | Vérifier l'état du fournisseur |
| `WAIT_OR_INVESTIGATE` | Réservation incertaine récente | Attendre la fenêtre réseau raisonnable puis vérifier |
| `CHECK_SUBMISSION_STATE` | Réservation encore `reserved` et ancienne | Déterminer si l'appel fournisseur a pu être envoyé |

Les seuils de 1 h et 24 h sont des seuils opérationnels initiaux, pas des garanties de Cloudflare.

## Procédure humaine
1. Exécuter la requête d'audit avec un rôle autorisé en lecture seule.
2. Identifier la réservation par `reservation_id`, `idempotency_key`, compte, modèle, worker et date UTC.
3. Examiner les journaux applicatifs corrélés à la clé d'idempotence et à la fenêtre temporelle.
4. Vérifier les journaux/rapports d'usage Cloudflare du compte et du modèle concernés. Une absence de réponse HTTP dans les logs PAPI ne prouve pas que Cloudflare n'a pas exécuté la requête.
5. Rassembler une preuve externe : requête absente, opération exécutée, ou résultat indéterminé.
6. Si l'opération est confirmée exécutée, faire valider la consommation par une personne autorisée avant commit avec les unités réelles/confirmées.
7. Si l'opération est prouvée non soumise, faire valider explicitement la libération par une personne autorisée.
8. Si les preuves sont contradictoires ou incomplètes, conserver l'état `uncertain` et le quota réservé.
9. Consigner l'identité de l'opérateur, la preuve, la décision, l'horodatage UTC et l'identifiant de réservation dans le système de tickets/audit approuvé.

## Interdictions
- Ne jamais transformer automatiquement `uncertain` en `released` après un délai.
- Ne jamais relancer la génération avec la même clé comme méthode de vérification.
- Ne jamais déduire « non exécuté » d'un timeout, d'une erreur réseau ou d'un HTTP 5xx.
- Ne jamais diminuer manuellement `reserved_units` ou augmenter `consumed_units` par UPDATE direct.
- Ne jamais exposer `SUPABASE_SERVICE_ROLE_KEY` dans un navigateur, une app mobile, un agent client ou les journaux.
- Ne pas donner aux rôles `anon` / `authenticated` accès aux tables ou RPC internes.

## Limite actuelle et prochaine évolution
La migration 013 ne possède pas encore de journal d'événements dédié à la réconciliation ni de RPC administrative à double validation. Cette mission ne crée pas de mutation SQL supplémentaire : le CLI Supabase n'est pas disponible dans l'environnement de travail pour générer correctement une migration avec `supabase migration new`, et aucun identifiant de projet n'autorise une opération sur une base réelle.

La prochaine évolution devra ajouter un journal append-only des décisions et des preuves, avec séparation des rôles demandeur/approbateur, sans `SECURITY DEFINER` par défaut. Toute fonction privilégiée éventuelle devra être justifiée, isolée et testée selon les recommandations Supabase actuelles.

## Vérification
Le harnais CI exécute la requête d'audit après la migration 013 et les tests SQL. Cette exécution vérifie que la requête est compatible avec le schéma de test ; elle ne valide pas les données d'un projet Supabase hébergé.
