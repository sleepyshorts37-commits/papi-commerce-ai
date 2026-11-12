# PAPI INCIDENT REPORTING BRIDGE 1.15

## Objectif
Transformer les diagnostics connus de Cheikh Fall (sortie de supervision worker) en événements d’incident **candidats**, compatibles avec le centre d’incidents et le validateur du journal d’audit.

## Contrat
- Entrée : rapport de supervision en lecture seule avec `as_of` horodaté et liste `issues`.
- Sortie : `report_candidates`, chacun contenant un événement `incident.reported` validable.
- Codes connus explicitement mappés vers gravité, catégorie, résumé et recommandation.
- Les anomalies inconnues sont ignorées et comptabilisées.
- Les champs libres et payloads sources ne sont jamais recopiés ; les recommandations sont issues d’une table locale contrôlée.
- Les identifiants sont déterministes pour un même instantané, code, portée et sujet.
- Les incohérences de portée, gravité, sujet ou statut d’action font échouer le traitement (fail-closed).

## Sécurité et limites
Ce module ne fait qu’une prévisualisation. Il n’appelle pas `append_event`, ne modifie pas le journal, ne notifie personne, ne relance aucun worker et ne déclenche aucune action externe. Les candidats doivent être examinés et leur persistance gérée séparément par un processus explicitement autorisé.

Aucun worker n’est démarré et aucun agent n’est activé par cette livraison. Aucune migration ou connexion Supabase n’est effectuée.
