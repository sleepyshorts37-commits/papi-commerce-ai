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

## Phase 3 — Première activité commerciale
- [ ] Comparer les opportunités sans frais initiaux.
- [ ] Vérifier éligibilité au Sénégal et moyens de paiement.
- [ ] Choisir une offre et un segment client.
- [ ] Préparer messages, livrables et suivi.
- [ ] Obtenir validation avant les premiers contacts externes.
- [ ] Mesurer les revenus réellement encaissés.

## Phase 4 — Extension
- [ ] PAPI BUSINESS PARTNERS.
- [ ] PAPI SERVICES et PAPI FREELANCE.
- [ ] PAPI AFFILIATION.
- [ ] PAPI MARKET et PAPI DROPSHIPPING.
- [ ] Intégrer les prestataires de paiement après validation de l'éligibilité, des frais, des permissions et des conditions.
- [ ] Mettre en place sauvegardes, rapprochement périodique et séparation des rôles comptables.

## PAPI WEB BUILDER
- [x] Modèles sectoriels de contenu pour entreprise, commerce, hôtellerie, services professionnels, éducation et santé (PR en revue).
- [x] Contrôle de complétude des faits obligatoires, avec validation humaine maintenue.
- [ ] Connecter les modèles au parcours de génération et réaliser une prévisualisation métier avec données validées.

## PAPI GLOBAL WORK
- [x] Définir le modèle de qualification des missions internationales, l'éligibilité pays, les politiques IA/automatisation et la priorité zéro coût initial.
- [x] Ajouter un évaluateur local qui ne soumet aucune candidature.
- [x] Ajouter le registre gouverné des sources, le contrat d’ingestion pré-collectée, la provenance et le dédoublonnage (Mission 17, Jour 1).
- [ ] Ajouter des connecteurs de recherche autorisés et tester les règles des plateformes.
- [ ] Vérifier concrètement l'éligibilité depuis le Sénégal et les moyens de paiement par plateforme.
- [ ] Développer le workflow de candidature avec autorisations explicites et preuve d'envoi.

## PAPI SOCIAL GROWTH
- [x] Définir les agents TikTok, Instagram, Facebook, YouTube et LinkedIn.
- [x] Définir leurs missions combinant publications, audience réelle, prospection, recherche de missions, ventes et suivi des conversions.
- [ ] Connecter les API officielles et autorisations de publication.
- [ ] Tester un calendrier éditorial et un parcours de conversion sans engagement artificiel.

## PAPI VIDEO TASKS
- [x] Définir dix profils d'analyse vidéo spécialisés.
- [x] Valider les liens YouTube et préparer une file de dix sous-tâches.
- [ ] Ajouter l'interface mobile de soumission de liens et l'historique.
- [ ] Connecter des sources de transcription/métadonnées autorisées et produire des rapports consolidés.
- [ ] Tester le flux complet sans visionnage répétitif ni génération artificielle de vues.

## PAPI OPEN SOURCE AI et autonomie
- [ ] Inventorier les modèles open source/open-weight, licences, exigences matérielles et compatibilité.
- [ ] Comparer les modèles sur des tâches représentatives de PAPI.
- [ ] Développer le routage multi-modèles et le fallback.
- [ ] Développer progressivement PAPI AUTONOMY ENGINE avec permissions, audit, arrêt d'urgence et supervision.
- [ ] Valider les opérations réelles avant toute autonomie externe.

## Mise en service
Un composant est opérationnel uniquement si code/configuration, accès autorisés, test reproductible, journaux et procédure d'arrêt sont présents.

## Statut
Fondations de code et documentation présentes. GLOBAL WORK dispose de validateurs et d’un contrat d’ingestion locale pré-collectée ; aucune collecte réseau ni candidature n’est encore active. VIDEO TASKS valide les liens et prépare une file, sans visionnage automatique. Les agents SOCIAL GROWTH et les dix analystes vidéo sont définis comme planifiés, pas déployés. Les agents SOCIAL GROWTH et les dix analystes vidéo sont définis comme planifiés, pas déployés. Le worker reste désactivé par défaut ; aucun agent autonome, scheduler permanent, compte social connecté, modèle IA externe ou paiement automatisé n'est actif.
