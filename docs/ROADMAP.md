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

## PAPI KIDS PUBLISHING — priorité ONE PROMPT → COMPLETE BOOK
- [x] Formaliser l'expérience cible, les rôles spécialisés, la chaîne de production, les livrables et les critères d'acceptation dans `docs/PAPI-KIDS-PUBLISHING-ONE-PROMPT.md`.
- [x] Définir un premier schéma JSON versionné du projet livre et des tâches, avec validation des dépendances.
- [x] Implémenter la création locale idempotente d’un projet depuis une seule requête et son plan de 13 tâches ; aucune tâche n’est exécutée.
- [x] Implémenter les transitions persistantes start/complete/fail/retry, le contrôle des dépendances, l'historique et la limite de tentatives (tests écrits, exécution encore requise).\n- [x] Ajouter les registres de livrables, rapports de revue indépendants et manifeste de livraison avec blocage avant approbation humaine.
- [x] Définir un contrat commun texte/image, un registre de fournisseurs et un mock local ; aucun fournisseur réel connecté (tests ajoutés, CI à confirmer).\n- [ ] Intégrer un fournisseur IA réel de texte et d'images après choix explicite, vérification des coûts, quotas, droits et secrets.
- [x] Ajouter le schéma, le contrôle structurel et l'assemblage Markdown des manuscrits (sans génération automatique du contenu).\n- [ ] Implémenter la génération IA des manuscrits et illustrations, ainsi que la couverture.\n- [x] Ajouter une épreuve PDF intérieure texte à coupe configurable (non certifiée KDP, sans images ni couverture).\n- [x] Ajouter un export EPUB 3 minimal et son inspection ZIP interne (validation EPUBCheck/KDP encore requise).
- [x] Ajouter les calculs de dos, dimensions de couverture avec fond perdu et marges minimales KDP (confirmation finale par le calculateur KDP toujours requise).\n- [x] Ajouter un rapport éditorial déterministe : validation structurelle, doublons de titres/paragraphes et avertissements de longueur (revue humaine toujours obligatoire).\n- [ ] Ajouter les contrôles qualité visuels, techniques approfondis et de propriété intellectuelle.
- [x] Assembler en une seule opération les exports Markdown, EPUB 3, PDF d'épreuve et manifeste avec empreintes (à partir d'un manuscrit fourni).\n- [ ] Réussir un test complet reproductible sur un livre pilote réellement généré par IA, illustré, préflighté et avec échec simulé/reprise.
- [ ] Obtenir l'approbation humaine avant toute publication KDP.

- [ ] Exécuter et valider les tests du cycle de vie, des livrables, des revues et du manifeste dans un environnement Python.\n\n## Mise en service
Un composant est opérationnel uniquement si code/configuration, accès autorisés, test reproductible, journaux et procédure d'arrêt sont présents.

## Statut
Fondations de code et documentation présentes. Le worker vérifie les identités Ed25519 en mode local par défaut, ou via un adaptateur Supabase explicitement injecté. Le schéma et l'adaptateur partagés sont codés et testés par simulation, mais aucun projet distant n'est configuré et aucune migration n'est exécutée. Aucun agent autonome, worker permanent, scheduler déployé, boutique, prospection externe ou paiement automatisé n'est actif. Aucun modèle IA n'est connecté à ce stade.

## PAPI CONNECT — intégrations économiques et open source
- [x] Mission 182 : architecture, règles de gouvernance et inventaire initial des projets open source dans `docs/PAPI-CONNECT-ARCHITECTURE.md`.
- [x] Mission 183 : schéma JSON, catalogue fournisseurs, validation locale, permissions et tests sans réseau dans `docs/PAPI-CONNECT-PROVIDER-REGISTRY.md`.
- [ ] Mission 184 : interfaces d'adaptateurs et fournisseur simulé, tests sans réseau.
- [ ] Mission 185 : premier fournisseur IA réel après choix et autorisation explicites, test non sensible.
- [ ] Mission 186 : attribution des outils à deux agents pilotes avec permissions minimales.
- [ ] Missions suivantes : observabilité, plafonds, fallback, automatisation et extension des fournisseurs.

