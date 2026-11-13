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
- [ ] Concevoir son moteur de génération, aperçu isolé, modification itérative et export de code source.\n  - [x] Ajouter un serveur de prévisualisation statique local, loopback-only, lecture seule, avec contrôles de chemins et en-têtes CSP ; tests HTTP automatisés.\n  - [ ] Ajouter des tests de rendu navigateur réel, captures responsive et régressions visuelles (le serveur local seul ne constitue pas cette preuve).\n  - Contrat d'architecture multi-pages ajouté : sitemap déterministe, routes sûres et traçabilité exigences → pages ; génération multi-pages et aperçu toujours à faire.
  - Socle partiel ajouté : génération statique déterministe, mises à jour structurées, contrôles locaux et export ZIP allowlisté ; aperçu navigateur isolé et moteur IA non implémentés (voir `docs/PAPI-WEB-BUILDER-MVP.md`).
- [ ] Ajouter des tests de qualité web, sécurité, responsive et critères d'acceptation.
- [ ] Atteindre le standard de création web agence/grande entreprise : direction artistique par projet, design system, architecture multi-pages, fonctionnalités réellement intégrées, responsive multi-écrans.
  - Première base visuelle premium ajoutée (composition éditoriale, tokens CSS, responsive tablette/mobile et fondamentaux clavier) ; ne constitue pas une livraison entreprise.
- [ ] Ajouter une chaîne de preuves qualité : tests navigateur, régression visuelle, accessibilité cible WCAG 2.2 AA, SEO, Core Web Vitals, sécurité et documentation de livraison.
  - Contrôles statiques de base ajoutés ; tests navigateur, audit WCAG réel, Core Web Vitals et revue de sécurité restent à construire.
- [ ] Définir les paliers Prototype / MVP / Production professionnelle / Entreprise-critique et bloquer toute déclaration de niveau sans preuves.
- [ ] Développer l'orchestration IA multi-spécialistes (design, frontend, backend, SEO, accessibilité, performance, sécurité, QA) avec contrôleur indépendant.

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


### PAPI WEB BUILDER — génération multi-pages (implémentation initiale)
- [x] Générateur statique multi-pages relié au contrat d'architecture : accueil + routes secondaires.
- [x] Navigation partagée, page active accessible, fil d'Ariane, CSS commun responsive.
- [x] Titres/descriptions SEO, sitemap XML et manifeste des fichiers produits.
- [x] Échappement HTML et vérification des liens internes dans un rapport qualité initial.
- [ ] Tests automatisés exécutés et validés en CI sur le commit de livraison.
- [ ] Validation CI des tests navigateur multi-viewport et captures (assertion de route corrigée, rerun requis), audit WCAG 2.2 AA, performance et sécurité.
- [ ] Formulaires/backend, intégrations métier, authentification, aperçu hébergé et déploiement.
- **Statut :** génération multi-pages implémentée, mais qualité entreprise non certifiée et aucune publication autorisée ou réalisée.


### PAPI WEB BUILDER — profils de design sectoriels
- [x] Six profils de marque contrôlés : corporate, e-commerce, hospitality, services professionnels, éducation et santé.
- [x] Tokens de couleur, accroches sectorielles et variantes de composition visuelle.
- [x] Sections réutilisables : hero, cartes de contenu, CTA de clôture, navigation et pied de page.
- [x] Tests ajoutés pour les profils, les tokens, l'échappement et la génération multi-pages.
- [ ] Exécution réelle des tests et validation CI sur le commit final.
- [ ] Images éditoriales, catalogue e-commerce, réservation, formulaires/backend et intégrations métier.
- [ ] Tests navigateur, revue responsive réelle, audit WCAG 2.2 AA et mesure Core Web Vitals.
- **Statut :** base de design sectorielle livrée ; aucune prétention de certification entreprise ou de mise en production.


### PAPI WEB BUILDER — sections éditoriales configurables
- [x] Ajouter un catalogue contrôlé de sections : intro, grille de fonctionnalités, statistiques, FAQ et CTA.
- [x] Autoriser des sections distinctes sur chaque page via un brief structuré.
- [x] Refuser HTML/CSS/scripts arbitraires et destinations CTA externes ; n'autoriser que les pages internes existantes.
- [x] Ajouter des composants sémantiques, styles responsives et tests unitaires/intégration.
- [ ] Confirmer le passage CI sur le commit final et traiter toute régression.
- [x] Ajouter des sections métier statiques (catalogue produits, équipe, témoignages avec provenance explicite, cartes de services) avec schémas de données validés.\n  - Réservation réelle, paiement, panier et formulaires connectés restent hors périmètre ; voir `docs/PAPI-WEB-BUILDER-BUSINESS-COMPONENTS.md`.
- [ ] Ajouter prévisualisation navigateur et tests visuels multi-viewport.
- **Statut :** catalogue de sections statiques personnalisables implémenté ; aucune fonctionnalité transactionnelle ou backend n'est incluse.


### PAPI WEB BUILDER — validation navigateur (cycle 5 jours)
- [x] Définir le programme de validation navigateur sur cinq jours (`docs/PAPI-WEB-BUILDER-BROWSER-VALIDATION-5-DAYS.md`).
- [x] Corriger le routage de la racine `/` vers `index.html` dans le serveur de prévisualisation local après analyse d'un échec CI réel.
- [x] Compléter les tests HTTP (GET, HEAD, ressources, chemins interdits) et valider la CI du correctif : 427 tests Python réussis sur `e2121acf4338da989e26550d43f86f842bc4feb6`.
- [x] Ajouter Playwright épinglé dans `requirements-browser-test.txt`, un workflow Chromium dédié et des tests de rendu réels sur un site synthétique.
- [x] Retirer l'appel Google Fonts externe et imposer des polices système locales ; le test navigateur vérifie désormais l'absence de requêtes tierces.
- [x] Confirmer le workflow Chromium sur `13acb342fcdf377f3f0b39fd30ddee5c66cc3b8b` : core tests, registre, documentation et Chromium tous réussis.
- [x] Ajouter tests mobile, tablette, desktop, navigation inter-pages, débordement horizontal et captures d'écran CI (validation du commit à venir).
- [ ] Ajouter les contrôles d'accessibilité automatisés et documenter les limites de validation humaine.
- [ ] Exécuter la suite finale et publier un rapport de recette technique.
- **Statut :** Jours 1 et 2 validés en CI sur `13acb342fcdf377f3f0b39fd30ddee5c66cc3b8b` ; tests responsive Jour 3 ajoutés, CI à confirmer. Aucun audit WCAG complet revendiqué.
