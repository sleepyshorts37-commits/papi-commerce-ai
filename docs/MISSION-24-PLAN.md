# Mission 24 — Observabilité sûre et opérations contrôlées de la file

## Objectif
Fournir une visibilité opérationnelle sûre sur la file d'exécution, renforcer les contrôles de sécurité et fiabiliser les procédures d'exploitation sans activer de traitement autonome.

## Programme étendu — 10 jours
1. Indicateurs agrégés de santé de la file.
2. Cohérence des transitions et visibilité des erreurs génériques.
3. Contrôles de rétention et purge simulée (preview-only).
4. Rapports de diagnostic et procédures de reprise manuelle.
5. Audit de sécurité et de fiabilité : privilèges, migrations, confidentialité, couverture CI PostgreSQL/PostgREST et correction des écarts.
6. Surveillance des performances PostgreSQL et seuils d'observation, sans scheduler permanent.
7. Gestion des incidents et alertes contrôlées, sans notification externe automatique.
8. Sauvegarde, restauration et continuité : procédures vérifiables et tests isolés.
9. Tests de résistance, concurrence et scénarios de panne.
10. Audit final, documentation des limites opérationnelles et clôture.

## État d'avancement
- Jours 1 à 5 : réalisés et validés par CI sur la branche de préparation.
- Jour 6 : protocole d'observation des plans PostgreSQL et probe read-only ajoutés ; CI finale requise.
- Jour 7 : classification des incidents, arbre de décision et modèle d'alerte manuelle documentés.
- Jour 8 : procédure d'exercice backup/restauration sur bases jetables documentée ; aucun backup de production.
- Jour 9 : matrice des scénarios de résilience et limites de test documentées ; coupure/redémarrage du conteneur non exécutés dans CI.
- Jour 10 : audit final et matrice des risques résiduels rédigés ; clôture conditionnée à la CI finale.

## Garde-fous non négociables
- Aucun worker permanent, scheduler ou boucle autonome.
- Aucune reprise automatique, purge réelle ou action externe.
- Aucun projet Supabase hébergé ni service Google connecté sans autorisation explicite.
- Aucun secret réel dans Git, tests ou journaux.
- Accès aux fonctions opérationnelles limité au rôle de service explicitement autorisé.
- Aucun merge ni déploiement sans approbation explicite.
- Les validations PostgreSQL/PostgREST restent isolées et ne prouvent pas qu'un projet Supabase hébergé est opérationnel.
