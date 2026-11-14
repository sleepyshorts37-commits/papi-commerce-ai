# Mission 24 — Jour 3 : rétention et simulation de purge

## Livrables
- Migration additive `008_queue_retention_preview.sql`.
- Fonction `papi_execution_queue_retention_preview(cutoff)` strictement en lecture seule.
- Seuls les jobs terminaux anciens (`done` et `failed`) sont comptés comme potentiellement éligibles.
- Les jobs `running`, `queued`, `retry` et les jobs terminaux récents sont classés comme protégés.
- Sortie limitée à des compteurs agrégés et au marqueur `preview_only`; aucun identifiant, clé d'idempotence, payload ou résultat.
- Permissions limitées à `service_role`.
- Test PostgreSQL jetable vérifiant la classification, l'absence de fuite, le refus d'une date future et l'absence de mutation.

## Validation
En attente de GitHub Actions sur le commit final de cette branche.

## Limites
Aucune suppression, modification de données, planification ou automatisation n'est implémentée. Aucun projet Supabase hébergé n'a été touché. Aucun merge ni déploiement.
