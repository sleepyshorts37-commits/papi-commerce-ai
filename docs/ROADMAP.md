# Plan de réalisation

## Phase 0 — Fondations documentaires
- [x] Vision et activités définies.
- [x] Gouvernance et limites de sécurité documentées.
- [ ] Résoudre les collisions de noms.
- [ ] Valider l'organigramme final.

## Phase 1 — Socle technique minimal
- [x] Registre agents et tâches avec validation.
- [x] Noyau de coordination, audit, machine à états et stockage.
- [x] File d'exécution contrôlée, handlers et worker à exécution désactivée.
- [x] Mémoire partagée locale.
- [x] Planificateur déterministe sans exécution autonome.
- [x] Outils commerciaux locaux : prospects, opportunités, offres, pipeline et interactions.
- [x] Registre financier append-only : recettes vérifiées, dépenses approuvées/payées, remboursements et rapports XOF.
- [x] Contrôle local de posture de sécurité et checklist de préparation au déploiement.
- [ ] Configurer les secrets et permissions d'hébergement après choix explicite du propriétaire.
- [ ] Effectuer une revue indépendante de sécurité et un test d'intrusion avant toute production.
- [ ] Tester un workflow non sensible de bout en bout dans un environnement déployé.

## Phase 2 — Coordination
- [x] Briefing déterministe d'Astou.
- [x] PAPI COMMAND CENTER local en lecture seule.
- [x] PAPI CHAT : socle local de communication interne.
- [x] Contrôle d'accès local : statut actif, permissions déclarées, interdictions et garde-fous globaux.
- [x] Prototype local d'authentification cryptographique HMAC-SHA256, horodatage et anti-rejeu.
- [x] Ajouter révocation et rotation locales des clés HMAC ; tests de rejet des identités révoquées et des signatures périmées.
- [x] Ajouter un prototype Ed25519, registre public versionné, révocation, rotation et tests unitaires.
- [x] Brancher Ed25519 au contrôle d'accès et au worker ; maintenir HMAC uniquement pour compatibilité transitoire.
- [x] Préparer dans le schéma SQL le registre central de clés publiques et l'anti-rejeu transactionnel partagé.
- [x] Lier la preuve signée à la tâche et au handler ; vérification avant exécution worker.
- [x] Implémenter un adaptateur runtime Supabase injectable pour vérifier les clés publiques et consommer les nonces via RPC (tests simulés).
- [ ] Exécuter les tests d'intégration sur un projet Supabase de test et valider les politiques/permissions avant production.
- [ ] Synchroniser mémoire et messages entre instances.
- [ ] Déployer et tester orchestration, scheduler et worker.

## Phase 3 — Premier lancement prioritaire : PAPI KIDS PUBLISHING
- [x] Définir les trois activités et les 24 postes cibles, avec chaîne éditoriale-commerciale et garde-fous IP/financiers (PR #225).
- [x] Ajouter le catalogue local versionné, les contrôles de fichiers SHA-256 et les portes droits/qualité/KDP/validation humaine (Mission 73 ; 180 tests unitaires et trois workflows CI réussis sur le SHA d'implémentation).
- [ ] Rattacher les 24 postes au registre central d'identités et vérifier l'unicité globale des identifiants/noms avant toute activation.
- [x] Ajouter un générateur local de kits de production vierges : brief, canevas de manuscrit, métadonnées, checklist et rapport qualité initial (Mission 74 ; 187 tests et trois workflows CI réussis sur le SHA de code testé 7bfc392e ; les commits suivants n'ont modifié que le rapport et la roadmap).
- [ ] Construire les outils de rédaction/assemblage des manuscrits, illustrations originales, intérieurs PDF, couvertures et exports finaux.
- [ ] Préparer cinq livres pilotes originaux et faire contrôler indépendamment chaque fichier.
- [ ] Vérifier les exigences KDP actuelles, l'éligibilité depuis le Sénégal, les moyens de versement, frais et retenues.
- [ ] Obtenir validation humaine explicite avant toute publication ou promotion externe.
- [ ] Réaliser le premier lancement manuel contrôlé ; aucun agent, compte ou publication externe n'est activé automatiquement.

## Phase 4 — Autres activités commerciales
- [ ] Comparer les opportunités sans frais initiaux.
- [ ] Vérifier éligibilité au Sénégal et moyens de paiement.
- [ ] Choisir une offre et un segment client.
- [ ] Préparer messages, livrables et suivi.
- [ ] Obtenir validation avant les premiers contacts externes.
- [ ] Mesurer les revenus réellement encaissés.

## Phase 5 — Extension
- [x] Documenter PAPI KIDS PUBLISHING : trois activités, 24 postes cibles, workflow éditorial-commercial, modèle sans stock et garde-fous IP/financiers.
- [ ] Rattacher les 24 postes au registre central d'identités et vérifier l'unicité globale des identifiants/noms avant toute activation.
- [x] Ajouter les premiers outils locaux de catalogue, briefs vierges, dossiers de fichiers et contrôles initiaux (Missions 73–74).
- [ ] Compléter les outils de rédaction, illustrations, mise en page PDF, coûts et rapports.
- [ ] Réaliser un pilote de livres originaux et vérifier les exigences KDP, l'éligibilité depuis le Sénégal et les moyens de versement.
- [ ] Obtenir une validation humaine explicite avant toute publication ou promotion externe.
- [ ] Tester les intégrations officielles et l'automatisation contrôlée après revue de sécurité.

- [ ] PAPI BUSINESS PARTNERS.
- [ ] PAPI SERVICES et PAPI FREELANCE.
- [ ] PAPI AFFILIATION.
- [ ] PAPI MARKET et PAPI DROPSHIPPING.
- [ ] Intégrer les prestataires de paiement après validation de l'éligibilité, des frais, des permissions et des conditions.
- [ ] Mettre en place sauvegardes, rapprochement périodique et séparation des rôles comptables.

## Mise en service
Un composant est opérationnel uniquement si code/configuration, accès autorisés, test reproductible, journaux et procédure d'arrêt sont présents.

## Statut
Fondations de code et documentation présentes. Le worker vérifie les identités Ed25519 en mode local par défaut, ou via un adaptateur Supabase explicitement injecté. Le schéma et l'adaptateur partagés sont codés et testés par simulation, mais aucun projet distant n'est configuré et aucune migration n'est exécutée. Aucun agent autonome, worker permanent, scheduler déployé, boutique, prospection externe ou paiement automatisé n'est actif. Aucun modèle IA n'est connecté à ce stade.
