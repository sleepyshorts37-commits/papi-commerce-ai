# Mission 24 — Procédure de diagnostic et reprise manuelle de la file

## 1. Préconditions et autorisations
- Intervention réservée à un opérateur humain autorisé.
- Confirmer l'environnement, l'incident, la fenêtre temporelle et l'autorisation avant toute action.
- Utiliser un rôle serveur approuvé ; ne jamais exposer la clé `service_role` dans un navigateur, un client mobile, un dépôt ou un ticket.
- Capturer l'heure UTC, l'identifiant de changement/ticket et l'approbateur dans le journal d'audit existant. Ne pas copier de payload, résultat, jeton ou code d'erreur secret dans les rapports.

## 2. Diagnostic sans effet de bord
1. Consulter le rapport agrégé `papi_execution_queue_diagnostic_report(cutoff)`.
2. Examiner les compteurs d'état, les baux expirés, l'âge du plus ancien travail prêt et les volumes d'erreurs par état.
3. Utiliser la prévisualisation de rétention uniquement pour évaluer les volumes ; elle ne supprime rien.
4. Comparer les compteurs à la fenêtre de l'incident et aux journaux applicatifs autorisés.
5. Si les indicateurs sont ambigus, arrêter et demander une investigation approfondie plutôt que d'inférer un identifiant ou une cause.

## 3. Reprise manuelle — procédure contrôlée
1. Identifier le job via l'outil opérationnel autorisé, hors du rapport agrégé, et vérifier son propriétaire, son statut, son nombre de tentatives et son bail.
2. Vérifier que le worker initial est arrêté ou qu'un bail est réellement expiré ; ne jamais reprendre un job `running` avec un bail valide.
3. Vérifier l'idempotence de l'opération métier et l'absence d'effet externe déjà exécuté.
4. Faire approuver explicitement la reprise par un responsable habilité ; conserver ticket, motif, périmètre et approbateur.
5. L'opérateur exécute l'action autorisée avec l'outil existant et les contrôles de bail/idempotence. Ce document ne fournit aucune commande de mutation ni API de reprise.
6. Vérifier ensuite le statut, l'audit et les effets métier ; consigner le résultat et arrêter en cas d'incohérence.

## 4. Actions interdites dans ce périmètre
- Pas de relance globale, de boucle de retry, de scheduler, de worker permanent ou de reprise automatique.
- Pas de modification directe de statut/jeton de bail pour contourner les contrôles.
- Pas de purge réelle : toute suppression nécessite un chantier distinct, une politique de rétention approuvée, une sauvegarde et une autorisation explicite.
- Pas de fusion, déploiement ou modification d'un projet Supabase hébergé sans approbation explicite.

## 5. Escalade
Escalader au responsable technique et suspendre toute reprise si : le propriétaire du bail est incertain, l'idempotence n'est pas démontrée, les compteurs divergent, un effet externe est ambigu, ou les permissions ne sont pas conformes.
