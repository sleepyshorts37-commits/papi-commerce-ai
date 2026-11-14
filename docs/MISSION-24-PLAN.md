# Mission 24 — Observabilité sûre et opérations contrôlées de la file

## Objectif
Donner aux responsables une visibilité opérationnelle sur la file de travaux sans exposer les données des tâches, les résultats, les identifiants internes ou les secrets, et sans activer de traitement autonome.

## Jour 1/5 — Indicateurs agrégés de santé de la file
- Ajouter une fonction PostgreSQL en lecture seule qui retourne uniquement des compteurs agrégés par statut, les baux expirés, les travaux prêts et l'âge du plus ancien travail prêt.
- Exclure strictement les identifiants, payloads, résultats, jetons de bail et détails d'erreur.
- Limiter l'exécution à service_role ; refuser anon, authenticated et PUBLIC.
- Tester les compteurs, les baux expirés, les permissions et l'absence de fuite sur PostgreSQL jetable.
- Ajouter la migration au workflow CI sans toucher à un projet hébergé.

## Jours suivants — périmètre prévu
- Jour 2 : cohérence des transitions et visibilité des erreurs génériques.
- Jour 3 : contrôles de rétention et purge simulée/preview-only.
- Jour 4 : rapports de diagnostic et procédures de reprise manuelle.
- Jour 5 : audit final, limites opérationnelles et clôture.

## Garde-fous
- Aucun worker permanent, scheduler ou boucle autonome.
- Aucune reprise manuelle automatisée et aucun effet externe.
- Aucun projet Supabase hébergé ou service Google connecté sans autorisation explicite.
- Aucun secret réel dans Git, les tests ou les journaux.
- Aucun merge ni déploiement sans approbation explicite.
