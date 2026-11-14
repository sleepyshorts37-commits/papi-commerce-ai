# Mission 20 — Jour 4/5 : adaptateur Supabase des PAPI AI WORKERS

## Architecture
Le dépôt possède déjà `SupabaseStore`, un transport PostgREST côté serveur. Le Jour 4 lui ajoute les opérations dédiées au registre central des workers. `SupabaseWorkerStore` est un adaptateur explicite construit autour d'une instance `SupabaseStore` déjà configurée ; aucun client, secret ou appel réseau n'est créé implicitement.

## Écriture
`SupabaseWorkerStore.sync_event(event, expected_version=...)` vérifie l'enveloppe et recalcule l'identifiant déterministe et la clé d'idempotence avant d'appeler `papi_sync_worker_record`. La fonction SQL du Jour 3 effectue snapshot, reçu d'événement et audit dans une transaction. La version attendue protège contre les écrasements concurrents. Aucun retry automatique n'est fait après une erreur réseau : l'appelant doit relire l'état et, si nécessaire, renvoyer le même événement avec la même clé d'idempotence.

## Lecture
`load_worker_inputs()` lit uniquement les trois domaines autorisés, avec une limite configurable plafonnée à 1 000 enregistrements par domaine. Les données sont normalisées en `platform_candidates`, `handoffs` et `profitability_results`. Les identifiants métiers sont reconstruits à partir de `record_id` si nécessaire. Les payloads contenant des champs sensibles connus sont rejetés.

## PAPI COMMAND CENTER
Par défaut, `build_command_center()` demeure en mode `read_only_local`, sans réseau. La lecture centralisée n'est activée qu'en injectant explicitement `worker_store=SupabaseWorkerStore(...)`. Dans ce mode, le rapport indique la lecture du stockage central et l'accès réseau. Les entrées worker explicites ne peuvent pas être combinées avec le stockage central, pour éviter les données contradictoires. Le tableau de bord ne déclenche aucune écriture, aucun worker et aucune action externe.

## Secrets et dépendances
La variable recommandée est `SUPABASE_SERVICE_ROLE_KEY`, côté backend uniquement. `SUPABASE_KEY` reste accepté pour compatibilité, mais doit aussi être une clé secrète serveur. Aucune dépendance Python Supabase supplémentaire n'est nécessaire : le dépôt utilise son transport HTTPS existant. La clé `service_role` contourne RLS et ne doit jamais être utilisée dans un navigateur, une application mobile ou un agent client.

## Vérifications
Les tests utilisent des stores simulés et vérifient les paramètres RPC, les trois lectures autorisées, le mapping des identifiants, les erreurs, les clés d'idempotence et le raccordement du Command Center. Aucun projet Supabase distant n'a été contacté par les tests de cette PR.
