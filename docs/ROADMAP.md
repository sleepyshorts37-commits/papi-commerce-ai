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
- [x] Prototype local d'authentification cryptographique HMAC-SHA256, horodatage et anti-rejeu.\n- [x] Ajouter révocation et rotation locales des clés HMAC ; tests de rejet des identités révoquées et des signatures périmées.
- [x] Ajouter un prototype Ed25519, registre public versionné, révocation, rotation et tests unitaires.
- [x] Brancher Ed25519 au contrôle d'accès et au worker ; maintenir HMAC uniquement pour compatibilité transitoire.
- [x] Préparer dans le schéma SQL le registre central de clés publiques et l'anti-rejeu transactionnel partagé.\n- [x] Lier la preuve signée à la tâche et au handler ; vérification avant exécution worker.
- [x] Implémenter un adaptateur runtime Supabase injectable pour vérifier les clés publiques et consommer les nonces via RPC (tests simulés).\n- [ ] Exécuter les tests d'intégration sur un projet Supabase de test et valider les politiques/permissions avant production.
- [ ] Synchroniser mémoire et messages entre instances.
- [ ] Déployer et tester orchestration, scheduler et worker.

## Phase 2B — Communication directe avec le propriétaire
- [x] Définir les contrats de conversation vocale STT/TTS et les profils vocaux distincts des IA chefs.
- [x] Définir les notifications e-mail proactives 24/7 limitées à l'adresse vérifiée du propriétaire.
- [x] Séparer notification propriétaire, e-mail tiers et permissions de session vocale.
- [x] Implémenter les interfaces techniques injectables et les tests simulés (tests CI en attente de fin d'exécution).
- [ ] Implémenter le routage allowlisté, les quotas, l'idempotence et l'audit.
- [ ] Effectuer la revue de sécurité et les tests avant activation.
- [ ] Connecter un fournisseur uniquement après choix et autorisation explicites du propriétaire.

## Phase 3 — PAPI DIGITALISATION & IA (nouveau département B2B)
- [x] Définir l'agent PAPI WEB BUILDER pour créer et modifier des sites web à partir d'un prompt, sans compétences en programmation.
- [ ] Concevoir son moteur de génération, aperçu isolé, modification itérative et export de code source.
  - Socle partiel ajouté : génération statique déterministe, mises à jour structurées, contrôles locaux et export ZIP allowlisté ; aperçu navigateur isolé et moteur IA non implémentés (voir `docs/PAPI-WEB-BUILDER-MVP.md`).
- [ ] Ajouter des tests de qualité web, sécurité, responsive et critères d'acceptation.
- [ ] Définir les intégrations hébergement/domaine et leur approbation avant toute publication.
- [x] Définir le catalogue : audit, conseil, intégration, accès employés, formation et support.
- [x] Définir le parcours client, la facturation par livrable et les revenus récurrents.
- [x] Documenter l'exemple de digitalisation d'une pharmacie et ses limites de sécurité.
- [x] Préparer une première grille de forfaits et tarifs indicatifs à partir de repères publics sénégalais ; validation terrain et calcul des coûts réels encore requis.
- [x] Définir les modèles de devis, contrat, cahier des charges, procès-verbal de recette et support.
- [x] Formaliser les portes de validation commerciale, les responsabilités et le dossier de preuve.
- [x] Concevoir les agents spécialisés et leurs fiches d'identité, permissions et responsables (registre et fiches documentaires ; instances non activées).
- [x] Construire une offre pilote avec démonstration sur données fictives et protocole de mesure (livrable documentaire ; aucun résultat réel mesuré).
- [x] Réaliser une revue de préparation commerciale, juridique, technique et sécurité ; documenter les blocages et le statut sans autoriser le lancement.
- [ ] Obtenir validation du propriétaire avant toute prospection, dépense ou engagement client.
- [ ] Réaliser un premier projet pilote autorisé et mesurer les revenus réellement encaissés.

## Phase 4 — Première activité commerciale
- [ ] Comparer les opportunités sans frais initiaux.
- [ ] Vérifier éligibilité au Sénégal et moyens de paiement.
- [ ] Choisir les offres et segments clients prioritaires.
- [ ] Préparer messages, livrables et suivi.
- [ ] Obtenir validation avant les premiers contacts externes.
- [ ] Mesurer les revenus réellement encaissés.

## Phase 5 — Extension
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
