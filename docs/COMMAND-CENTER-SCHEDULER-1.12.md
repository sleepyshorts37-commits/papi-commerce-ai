# PAPI COMMAND CENTER — intégration scheduler 1.12

## Intégration
Le tableau de bord peut recevoir un `scheduler_snapshot` explicite contenant exactement :
- `jobs` : instantané de la file ;
- `workers` : registre des workers et identités ;
- `as_of` : horodatage ISO-8601 avec fuseau ;
- `handlers` : registre des handlers et permissions ;
- `policy` : politique d'exécution.

Le tableau de bord transmet ces données au planificateur 1.11 et expose son résultat sous `worker_scheduler`.

## Comportement par défaut
Sans instantané fourni, le statut est `not_configured`. Le tableau de bord ne déduit pas les workers depuis le registre des agents et ne fabrique pas de jobs.

Avec un instantané valide, le statut est `preview_available`. Les décisions sont un aperçu en lecture seule. Avec la politique actuelle (`execution_enabled=false`), les jobs admissibles sont retenus.

## Sécurité
Aucune connexion Supabase, réservation, heartbeat, exécution de handler ou création de processus. Les contrôles exposent zéro réservation et zéro handler exécuté. Le planificateur ne constitue pas un moteur de production ni un runtime actif.
