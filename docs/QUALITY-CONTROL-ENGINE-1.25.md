# PAPI QUALITY CONTROL ENGINE — Phase 1.25

## Objectif
Centraliser les revues qualité explicites des livrables et empêcher qu'une tâche sans revue soit présentée comme validée.

## Fonctionnement
- Associe les événements `quality.reviewed` aux tâches connues.
- Distingue `review_passed`, `review_failed`, `rework_required`, `awaiting_review` et `not_reviewed`.
- Retient la revue valide la plus récente par tâche.
- Vérifie la cohérence des compteurs de critères et conserve les références de preuve.
- Prépare des candidats de revue structurée ; une validation n'est proposée que si tous les critères déclarés sont satisfaits.

## Sécurité et limites
- Lecture seule : aucun événement n'est écrit, aucune tâche n'est modifiée et aucune notification n'est envoyée.
- Le moteur ne lit pas le contenu réel des fichiers livrés et ne certifie pas leur véracité ; il projette des résultats de revue explicitement consignés.
- La référence de preuve est un identifiant documentaire, pas une preuve cryptographique.
- L'authentification du réviseur et l'approbation du propriétaire ne sont pas réalisées par ce module.
- Les tests sont ajoutés mais doivent être exécutés ; l'intégration et la CI doivent être vérifiées séparément.

## Déploiement
Cette phase ne déploie aucun agent, worker ou service et n'applique aucune migration Supabase.
