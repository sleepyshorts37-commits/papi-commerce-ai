# Mission 24 — Jour 5 : audit de sécurité et de fiabilité

## Périmètre audité
- Migrations de santé, transitions, rétention et diagnostic (006 à 009).
- Contrôle des permissions des fonctions opérationnelles.
- Confidentialité des sorties : agrégats uniquement, sans identifiants de tâches, payloads, résultats, jetons ou codes d'erreur détaillés.
- Caractère non mutatif des fonctions de santé, rétention et diagnostic.
- Ordonnancement des migrations et couverture des tests dans les deux jobs CI.

## Écarts détectés et corrections
1. Le job PostgreSQL jetable appliquait deux fois les migrations 004 et 005. Les appels redondants ont été supprimés pour rendre l'ordre d'installation déterministe.
2. Le job d'intégration PostgREST local ne chargeait pas les migrations 006 à 009 et ne testait donc pas les contrats de diagnostic de la file dans ce chemin. Les quatre migrations sont maintenant appliquées dans l'ordre et le test SQL du rapport de diagnostic est exécuté sur cette base isolée.

## Contrôles de sécurité retenus
- Les fonctions opérationnelles restent réservées à `service_role`; `PUBLIC`, `anon` et `authenticated` ne doivent pas recevoir EXECUTE.
- Les fonctions de lecture utilisent les propriétés de sécurité définies dans leurs migrations et fixent leur `search_path`.
- La prévisualisation de rétention ne supprime aucune ligne.
- Le rapport de diagnostic indique explicitement qu'une intervention humaine est requise et que la reprise automatique est désactivée.
- Les tests vérifient l'absence de fuite de champs sensibles et l'absence de mutation des enregistrements.

## Validation CI
Le workflow vérifie désormais les migrations 006 à 009 et le test `test_queue_diagnostic_report.sql` aussi dans le chemin PostgREST local. La validation finale de ce commit reste requise avant de déclarer le Jour 5 terminé.

## Limites
- Les tests tournent sur des bases PostgreSQL/PostgREST jetables et locales à CI.
- Aucun projet Supabase hébergé, compte Google, secret de production ou service externe n'a été utilisé.
- Aucun worker, scheduler, alerte externe, reprise automatique, purge réelle, merge ou déploiement n'est activé.
