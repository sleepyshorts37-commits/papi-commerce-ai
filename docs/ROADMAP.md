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

## Mise en service
Un composant est opérationnel uniquement si code/configuration, accès autorisés, test reproductible, journaux et procédure d'arrêt sont présents.

## Statut
Fondations de code et documentation présentes. Le worker vérifie les identités Ed25519 en mode local par défaut, ou via un adaptateur Supabase explicitement injecté. Le schéma et l'adaptateur partagés sont codés et testés par simulation, mais aucun projet distant n'est configuré et aucune migration n'est exécutée. Aucun agent autonome, worker permanent, scheduler déployé, boutique, prospection externe ou paiement automatisé n'est actif. Aucun modèle IA n'est connecté à ce stade.


### PAPI WEB BUILDER — audit SEO statique (cycle 5 jours)
- [x] Définir le périmètre et les critères de contrôle SEO local.
- [x] Ajouter l'auditeur HTML en lecture seule : titre, description, langue, H1, liens internes, canonical et Open Graph.
- [x] Vérifier le sitemap XML, robots.txt, les chemins et les liens symboliques.
- [x] Ajouter six tests unitaires et le guide de correction SEO.
- [ ] Exécuter les tests ciblés et la CI complète sur le commit final.
- [ ] Publier le rapport final après vérification des workflows.
- **Statut provisoire :** moteur et tests ajoutés sur `papi-web-builder-seo-audit-main-2026-11-13`. Aucun réseau, publication, merge ou déploiement ; la CI doit confirmer le cycle.
