# Plan de réalisation

## Phase 0 — Fondations documentaires
- [x] Vision et activités principales définies.
- [x] Gouvernance et limites de sécurité documentées.
- [ ] Résoudre les collisions de noms historiques.
- [ ] Valider l'organigramme final et les responsabilités.

## Phase 1 — Socle technique minimal
- [x] Registre agents et tâches avec validation.
- [x] Noyau de coordination, audit, machine à états et stockage local.
- [x] File d'exécution contrôlée, handlers et worker désactivé par défaut.
- [x] Mémoire partagée locale.
- [x] Planificateur déterministe sans exécution autonome.
- [x] Outils commerciaux locaux : prospects, opportunités, offres, pipeline et interactions.
- [x] Registre financier append-only et rapports XOF en lecture seule.
- [x] Contrôle local de posture de sécurité et checklist de préparation au déploiement.
- [ ] Configurer les secrets et permissions d'hébergement après choix explicite du propriétaire.
- [ ] Effectuer une revue indépendante de sécurité et un test d'intrusion avant toute production.
- [ ] Tester un workflow non sensible de bout en bout dans un environnement isolé.

## Phase 2 — Coordination et identité
- [x] Briefing déterministe d'Astou et PAPI COMMAND CENTER local en lecture seule.
- [x] Socle local de communication interne PAPI CHAT.
- [x] Contrôle d'accès local, permissions déclarées et interdictions globales.
- [x] Prototypes HMAC-SHA256 et Ed25519, révocation, rotation et anti-rejeu local.
- [x] Liaison de la preuve signée à la tâche et au handler, vérification avant exécution.
- [x] Adaptateur Supabase injectable pour vérifier les clés publiques et consommer les nonces via RPC (tests simulés).
- [ ] Exécuter les tests d'intégration sur un projet Supabase de test et valider les politiques/permissions.
- [ ] Mettre en place une synchronisation inter-instance de la mémoire et des messages.
- [ ] Déployer et tester orchestration, scheduler et worker dans un environnement de test.

## Phase 3 — Qualification commerciale sans frais initiaux
- [ ] Comparer des opportunités accessibles depuis le Sénégal, sans frais initiaux.
- [ ] Vérifier les conditions d'éligibilité, les moyens de paiement et les contraintes territoriales.
- [ ] Choisir une seule offre prioritaire et un segment client test.
- [ ] Préparer les livrables, messages, coûts, risques et indicateurs.
- [ ] Obtenir l'autorisation requise avant tout contact, publication ou engagement externe.
- [ ] Distinguer prospects, commandes, paiements annoncés et revenus réellement encaissés.

## Phase 4 — Pilotes de recherche des nouvelles activités
Les trois activités ci-dessous sont des propositions documentées dans la PR #86. Elles ne sont ni des départements opérationnels ni des agents activés.

### 4.1 Promotions, coupons et vouchers
- [ ] Définir le schéma de données d'une offre : source officielle, date de vérification, territoire, échéance, conditions, transférabilité et statut.
- [ ] Construire un processus de vérification et de mise en quarantaine des offres incertaines.
- [ ] Identifier des programmes d'affiliation ou de distribution explicitement autorisés.
- [ ] Tester la qualité des informations en mode recherche uniquement.
- [ ] N'autoriser une commercialisation qu'après vérification des droits de transfert/revente et validation humaine.

### 4.2 Développement logiciel et missions freelance
- [ ] Définir le processus produit : besoin, périmètre, estimation, architecture, prototype, tests, revue sécurité et documentation.
- [ ] Créer une grille de qualification des missions freelance accessibles au profil réel du propriétaire.
- [ ] Définir les faits de profil et éléments de portfolio vérifiables utilisables dans les candidatures.
- [ ] Préparer des prototypes et candidatures en brouillon uniquement.
- [ ] Exiger une autorisation avant soumission, contrat, engagement de délai, dépense ou accès à un environnement client.

### 4.3 Concours, prix et récompenses
- [ ] Définir une fiche d'opportunité : organisateur officiel, règlement, échéances, éligibilité Sénégal, frais, prix et clauses de propriété intellectuelle.
- [ ] Prioriser les concours gratuits et les organisateurs vérifiables.
- [ ] Mettre en place un contrôle anti-fraude et une revue des clauses avant toute participation.
- [ ] Préparer dossiers et prototypes sans soumission automatique.
- [ ] Exiger une validation avant frais, déplacement, soumission engageante ou acceptation d'un prix assorti de conditions.

## Phase 5 — Extension des activités
- [ ] PAPI BUSINESS PARTNERS.
- [ ] PAPI SERVICES et PAPI FREELANCE.
- [ ] PAPI AFFILIATION.
- [ ] PAPI MARKET et PAPI DROPSHIPPING.
- [ ] Promotions et vouchers, après validation des droits et du modèle économique.
- [ ] Concours et récompenses, après validation des règles et de l'éligibilité.
- [ ] Intégrer les prestataires de paiement après validation de l'éligibilité, des frais, des permissions et des conditions.
- [ ] Mettre en place sauvegardes, rapprochement périodique et séparation des rôles comptables.

## Conditions de passage en production
Un composant n'est déclaré opérationnel que si son code et sa configuration sont présents, ses accès sont autorisés, ses tests sont reproductibles, ses journaux sont vérifiables et une procédure d'arrêt existe. Une documentation ou une PR ne prouve pas qu'un service est déployé.

## Règles permanentes
- Aucun agent ne peut retirer, transférer, payer, acheter ou engager des fonds de façon autonome.
- Aucun abonnement, API payante, publicité, dépense, contrat ou engagement commercial sans autorisation explicite.
- Aucun agent ne peut falsifier identité, expérience, éligibilité, résultats ou preuves.
- Les secrets, mots de passe, tokens, OTP, PIN et CVV ne doivent jamais être enregistrés dans le dépôt.
- Les revenus ne sont reconnus qu'après vérification effective de l'encaissement.
- Les agents restent en mode recherche/préparation tant que leurs permissions d'exécution n'ont pas été explicitement accordées.

## Statut actuel
Les fondations de code et la documentation sont présentes. Le worker vérifie les identités Ed25519 en mode local par défaut, ou via un adaptateur Supabase explicitement injecté. Le schéma et l'adaptateur partagés sont codés et testés par simulation, mais aucun projet distant n'est configuré et aucune migration n'est exécutée. Aucun agent autonome, worker permanent, scheduler déployé, boutique, prospection externe ou paiement automatisé n'est actif. Aucun modèle IA n'est connecté à ce stade.
