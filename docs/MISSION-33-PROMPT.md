# Mission 33 — PAPI CONTROLLED SYNC & RECONCILIATION GATE
## Prompt d'exécution unique — programme de 20 journées

### Contexte vérifié
La Mission 32 fournit des adaptateurs explicites Supabase pour la mémoire et le chat, une pagination keyset et un lecteur mémoire à visibilité filtrée. Le dépôt possède aussi une identité Ed25519 partagée, un aperçu de réconciliation sans écriture et un rapport de préparation. La feuille de route indique toutefois qu'aucun projet Supabase de test n'a été validé, qu'aucun test inter-instances réel n'a été exécuté et qu'aucun mécanisme de transfert contrôlé n'est autorisé. La présente mission ferme d'abord les lacunes de protocole et de gouvernance ; elle ne prétend pas rendre un environnement distant opérationnel.

### Objectif général
Construire une chaîne de synchronisation inter-instances explicite, déterministe, observable et gouvernée : audit des snapshots, empreintes canoniques, plan de transfert sans contenu sensible, traitement des conflits, approbation humaine liée au périmètre, reprise/idempotence, validation de l'environnement, documentation d'exploitation et critères de mise en service. La synchronisation effective reste désactivée tant que les validations externes et l'autorisation explicite du propriétaire ne sont pas obtenues.

### Programme des 20 journées

#### Phase A — Contrats et sécurité (jours 1 à 5)
1. Auditer les modules mémoire/chat, identités, pagination, réconciliation, readiness et migrations 004–016.
2. Définir les contrats de snapshot, les identifiants stables, les limites de taille et les champs sémantiques comparés.
3. Définir une canonicalisation JSON déterministe et des empreintes SHA-256 indépendantes de l'ordre des clés.
4. Formaliser les frontières de visibilité : mémoire shared/agent, messages broadcast/direct, exclusion owner/restricted.
5. Établir le modèle de menace, les limites de service_role, les règles anti-secret et les critères d'arrêt.

#### Phase B — Planification déterministe (jours 6 à 10)
6. Transformer les écarts local_only/remote_only en références d'actions, sans embarquer le contenu.
7. Exclure les entrées identiques ; classer les conflits comme bloquants et ne jamais choisir automatiquement une version.
8. Générer des identifiants d'action et un digest de plan reproductibles et liés à l'agent et à la destination.
9. Ajouter validation d'intégrité du plan, limites de taille, validation d'identifiants et détection de doublons.
10. Ajouter tests adversariaux : acteur incohérent, payload altéré, duplication, secret, limite dépassée et contournement des conflits.

#### Phase C — Approbation et reprise gouvernées (jours 11 à 15)
11. Définir un contrat d'approbation humaine à périmètre fixe : digest, destination, actions et expiration.
12. Réutiliser les mécanismes d'approbation existants ; ne pas inventer une identité propriétaire ni accepter un booléen fourni par un agent.
13. Définir l'idempotence des opérations futures et les clés de déduplication par action.
14. Définir les états futurs d'une exécution : proposed, approved, applying, completed, partial, blocked, expired.
15. Documenter les scénarios crash/retry, conflit de version, lease expiré, résultat inconnu et procédure de reprise manuelle.

#### Phase D — Validation opérationnelle et transfert (jours 16 à 20)
16. Préparer un environnement Supabase jetable avec identités et données fictives, sans utiliser de données client.
17. Établir une matrice de tests multi-instances : permissions, visibilité, pagination, concurrence, rejeu et restauration.
18. Définir observabilité sans contenu : compteurs, latence, erreurs catégorisées, correlation IDs et alertes.
19. Documenter le runbook de validation, sauvegarde, restauration, arrêt d'urgence, rotation des clés et retour arrière.
20. Faire la revue finale de sécurité, vérifier les tests sur le SHA exact, mettre à jour la feuille de route et remettre une PR draft non fusionnée.

### Livrables obligatoires
- Module Python de génération de plans déterministes sans écriture.
- Tests unitaires et adversariaux couvrant les invariants de sécurité.
- Prompt et plan détaillés des 20 jours.
- Contrats d'approbation, idempotence, reprise, observabilité et validation environnementale documentés.
- Rapport d'exécution distinguant clairement code livré, tests CI, tests simulés et validations non réalisées.
- PR draft ouverte, non fusionnée, basée sur `mission-32-memory-chat-sync`.

### Gouvernance non négociable
- Aucun rôle, mission, hiérarchie, responsabilité ou permission d'agent n'est modifié.
- Aucun agent ne peut s'auto-approuver, s'auto-accorder des droits ou changer la politique de sécurité.
- Aucun transfert de données, aucune écriture Supabase, aucune migration distante, aucun déploiement.
- Aucun worker, scheduler, agent autonome ou tâche permanente activé.
- Aucun email, WhatsApp, DM, prospection, publication ou contact client.
- Aucune dépense, souscription, publicité, paiement, transfert ou retrait.
- Aucun secret, donnée client, donnée personnelle ou contenu réel de mémoire/chat dans GitHub.
- Les approbations doivent être vérifiées côté serveur et liées au digest exact ; un simple champ `approved=true` ne constitue jamais une preuve.
- En cas de conflit, identité non vérifiée, snapshot incomplet ou erreur réseau, échouer en mode fermé.
- Ne jamais annoncer un test distant ou une synchronisation réelle sans preuve reproductible.

### Critères d'acceptation
1. Les plans sont déterministes, référentiels et ne contiennent aucun contenu de mémoire/message.
2. Les conflits ne deviennent jamais des actions de copie.
3. Les actions exigent une approbation humaine hors du contrôle de l'agent.
4. Les digests détectent toute altération du plan.
5. Les entrées invalides, doublons et limites dépassées sont refusés.
6. Les tests unitaires et CI passent sur le SHA exact final.
7. Les limites des tests simulés et l'absence de validation distante sont explicites.
8. La PR reste draft, ouverte et non fusionnée.
