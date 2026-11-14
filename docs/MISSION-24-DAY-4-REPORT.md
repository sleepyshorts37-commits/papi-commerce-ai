# Mission 24 — Jour 4 : diagnostics et reprise manuelle contrôlée

## Livrables
- Migration additive `009_queue_diagnostic_report.sql` : rapport agrégé regroupant santé, synthèse d'erreurs et aperçu de rétention.
- Aucun identifiant de job, payload, résultat, jeton ou code d'erreur détaillé dans le rapport.
- Marqueurs explicites `manual_action_required=true` et `automated_recovery_enabled=false`.
- Fonction accessible uniquement à `service_role`.
- Test SQL vérifiant les sections, la confidentialité, les permissions et l'absence de mutation.
- Runbook documentant le diagnostic, l'approbation humaine, les vérifications d'idempotence/bail, la reprise via outils autorisés et l'escalade.

## Validation
En attente de GitHub Actions sur le commit final de cette branche.

## Limites
Aucune API ou commande de reprise n'est créée. Aucune mutation, purge, automatisation, modification d'un projet Supabase hébergé, fusion ou déploiement.
