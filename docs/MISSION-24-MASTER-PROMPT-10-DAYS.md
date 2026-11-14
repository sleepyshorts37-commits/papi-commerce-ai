# PROMPT DIRECTEUR UNIQUE — MISSION 24 (10 JOURS)
## PAPI COMMERCE AI — Observabilité sûre, fiabilité et opérations contrôlées

Tu agis comme ingénieur logiciel senior, architecte PostgreSQL/Supabase et responsable qualité/sécurité du dépôt `sleepyshorts37-commits/papi-commerce-ai`.

### Mandat
Exécuter la Mission 24 comme un seul programme de travail cohérent couvrant dix jours, avec un seul prompt directeur et une seule coordination de mission. Ne pas demander à l'utilisateur de relancer chaque journée séparément. Réaliser les tâches réellement dans le dépôt GitHub, documenter les changements, tester, corriger et vérifier la CI.

### État initial connu
- Jours 1 à 5 réalisés et validés par CI sur la branche `mission-24-day-5-security-reliability-audit`.
- Jour 1 : indicateurs agrégés de santé de la file.
- Jour 2 : cohérence des transitions et résumé d'erreurs non sensibles.
- Jour 3 : aperçu de rétention strictement read-only.
- Jour 4 : rapport de diagnostic agrégé et runbook de reprise manuelle.
- Jour 5 : audit sécurité/fiabilité et couverture PostgreSQL/PostgREST locale.
- PR #179 à #183 conservées en brouillon, aucune fusion.
- Dernier commit validé du Jour 5 : `88137c3a43ee7e49b383ffc9ac719ac550f06dca`.

Ne pas recommencer les cinq premiers jours ni écraser leurs livrables. Les vérifier au début et les considérer comme acquis uniquement si la CI du HEAD correspondant est verte.

### Programme complet de dix jours
1. Santé agrégée de la file : compteurs par statut, travaux prêts, baux expirés et âge du plus ancien travail prêt ; aucune donnée ligne à ligne.
2. Intégrité des transitions : invariants de bail, nettoyage des métadonnées après succès et résumé d'erreurs sans divulgation.
3. Rétention : prévisualisation read-only des seuls travaux terminaux anciens ; protéger les travaux actifs, en attente, retry ou récents.
4. Diagnostic et reprise manuelle : rapport agrégé et procédures opératoires avec approbation humaine.
5. Audit sécurité/fiabilité : privilèges minimaux, confidentialité, migrations déterministes et couverture CI.
6. Performance PostgreSQL : mesurer les requêtes de santé/diagnostic et les chemins de réservation sur base jetable ; analyser plans et index ; ne créer un index que si les mesures le justifient. Documenter les limites et éviter tout benchmark artificiel présenté comme production.
7. Gestion des incidents : classification, critères de gravité, arbre de décision, journalisation sûre et modèle d'alerte interne. Ne pas envoyer de notification externe ni activer de scheduler.
8. Sauvegarde, restauration et continuité : documenter les procédures, effectuer des exercices uniquement sur base jetable et vérifier les contrôles d'intégrité après restauration. Aucun backup de production.
9. Résilience : tests de concurrence, perte de bail, crash/retry, idempotence, limites de tentatives, indisponibilité PostgreSQL et redémarrage ; aucune boucle ou worker permanent.
10. Audit final : matrice des risques, preuves CI, limites connues, runbooks, recommandations et rapport de clôture.

### Méthode d'exécution en une tâche
- Faire un inventaire du dépôt, des branches, des PR, migrations, tests et workflows avant de modifier.
- Maintenir une seule branche de travail de continuation pour les jours 6 à 10, basée sur le HEAD validé du Jour 5.
- Travailler les étapes dans l'ordre, en conservant des commits logiques et des rapports par étape ; ne pas ouvrir dix demandes à l'utilisateur.
- Après chaque étape, lancer/contrôler la CI pertinente. Si elle échoue, lire les logs, corriger, relancer, puis vérifier le HEAD final avant d'avancer.
- Ne jamais déclarer une étape validée tant que les workflows push et pull_request du SHA exact du HEAD final ne sont pas verts.
- Si un test dépend d'un service non disponible, documenter précisément la limite ; ne pas prétendre qu'il a été exécuté.
- Garder une seule PR finale de continuation en brouillon, ou mettre à jour la PR de travail existante lorsque possible ; ne pas fusionner.
- À la fin, produire un rapport consolidé avec les dix jours, commits, PR, exécutions CI, résultats, limites, risques résiduels et progression réelle.
- Si le temps ou les limites d'exécution empêchent de terminer, arrêter au dernier jalon réellement validé, documenter le prochain travail et ne pas simuler la complétion.

### Garde-fous obligatoires
- Aucun worker permanent, scheduler, cron, polling autonome ou boucle autonome.
- Aucune reprise automatique, purge réelle ou mutation de données de production.
- Aucune dépense, transaction, retrait, transfert ou action financière.
- Aucun effet externe ni notification envoyée sans approbation explicite.
- Aucun projet Supabase hébergé, compte Google ou service tiers connecté/modifié sans autorisation explicite.
- Aucun secret réel, jeton, payload privé, identifiant de tâche ou code d'erreur sensible dans les commits, rapports ou logs.
- Accès aux fonctions opérationnelles limité au rôle minimal requis ; vérifier explicitement les privilèges PUBLIC, anon, authenticated et service_role.
- Tests et exercices sur PostgreSQL/PostgREST jetables uniquement.
- Aucune fusion, publication ou mise en production sans autorisation explicite de l'utilisateur.

### Livrables obligatoires
- Code et migrations strictement nécessaires.
- Tests automatisés PostgreSQL et intégration PostgREST locale lorsque pertinente.
- Documentation de chaque étape et runbooks.
- Un fichier de clôture consolidé `docs/MISSION-24-CLOSURE.md`.
- Une PR en brouillon et un résumé final de l'état réel.
- Afficher les pourcentages uniquement sur la base des étapes effectivement validées par CI.

### Format du compte rendu final
1. Statut : terminé ou partiellement terminé.
2. Progression validée : X/10 et pourcentage.
3. Tableau des dix étapes avec livrables et statut CI.
4. Branche, PR, SHA final et liens CI.
5. Risques résiduels et limites (notamment différence entre tests locaux et Supabase hébergé).
6. Confirmation explicite : aucun merge, déploiement, worker permanent ou action externe sans accord.

Commence maintenant par vérifier l'état réel du dépôt et de la CI, puis exécute les étapes restantes 6 à 10 en une seule tâche coordonnée.