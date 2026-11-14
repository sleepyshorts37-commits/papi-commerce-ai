# Plan de réalisation

## Phase 0 — Fondations documentaires
- [x] Vision et activités définies.
- [x] Gouvernance et limites de sécurité documentées.
- [x] Résoudre les collisions de noms (clarification du registre, Mission 35).
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
- [x] PAPI CHAT : socle local de communication interne, journal append-only validé (Mission 37).
- [x] Contrôle d'accès local : statut actif, permissions déclarées, interdictions et garde-fous globaux.
- [x] Prototype local d'authentification cryptographique HMAC-SHA256, horodatage et anti-rejeu.
- [x] Ajouter révocation et rotation locales des clés HMAC ; tests de rejet des identités révoquées et des signatures périmées.
- [x] Ajouter un prototype Ed25519, registre public versionné, révocation, rotation et tests unitaires.
- [x] Brancher Ed25519 au contrôle d'accès et au worker ; maintenir HMAC uniquement pour compatibilité transitoire.
- [x] Préparer dans le schéma SQL le registre central de clés publiques et l'anti-rejeu transactionnel partagé.
- [x] Lier la preuve signée à la tâche et au handler ; vérification avant exécution worker.
- [x] Implémenter un adaptateur runtime Supabase injectable pour vérifier les clés publiques et consommer les nonces via RPC (tests simulés).
- [ ] Exécuter les tests d'intégration sur un projet Supabase de test et valider les politiques/permissions avant production.
- [ ] Synchroniser mémoire et messages entre instances (contrat Mission 38 + paquet référentiel Mission 39 + approbation Ed25519 Mission 40 + registre local de reçus Mission 41 + consommation nonce/reçu atomique SQLite Mission 42 + spool local hors ligne Mission 43 + réception locale authentifiée et reçu atomique Mission 44 + charge utile de contenu contrôlée et liée au digest approuvé Mission 45 + import local SQLite avec nonce/reçu/contenu atomiques Mission 46 + lecteurs mémoire/chat en lecture seule Mission 47 + journaux SQLite locaux facultatifs Mission 48 + migration JSONL vers SQLite sauvegardée, atomique et idempotente Mission 49; transport réseau, exécution de migration approuvée sur l'instance cible et tests multi-instance encore requis).
- [ ] Déployer et tester orchestration, scheduler et worker.
- [x] Ajouter des outils locaux de sauvegarde SQLite, vérification SHA-256/intégrité et restauration contrôlée vers un nouveau chemin (Mission 50).
- [x] Ajouter chiffrement authentifié AES-256-GCM, vérification et rotation locale des clés de sauvegarde SQLite (Mission 51 ; 466 tests et CI réussis).
- [x] Authentifier les métadonnées du manifeste AES-GCM v2, valider strictement son schéma et préserver la lecture v1 (Mission 52 ; 469 tests et CI réussis sur le SHA final).
- [x] Préparer un manifeste de transfert local déterministe liant paquet .papisync et charge utile .papidata, avec digests, destination, limites et validation stricte ; aucun réseau ni import (Mission 53).
- [x] Vérifier les fichiers réels contre le manifeste de transfert, refuser les fichiers absents/modifiés/symboliques et appliquer des contrôles stricts de types et tailles (Mission 54 ; vérification locale uniquement).
- [x] Ajouter un précontrôle local complet du transfert : fichiers, charge utile, destination et signature Ed25519 du propriétaire, sans écrire de reçu ni consommer le nonce (Mission 55).
- [x] Construire localement une requête de transport HTTPS canonique, allowlistée et idempotente, avec fichiers encodés et contrôles anti-SSRF initiaux, sans émission réseau (Mission 56).
- [x] Définir et vérifier localement le reçu de transport signé Ed25519, lié au digest exact de la requête et à la livraison, avec anti-rejeu du nonce destinataire ; aucune connexion réseau ni import (Mission 57).
- [x] Archiver les reçus de transport vérifiés dans un registre SQLite local idempotent et protégé contre les collisions (Mission 58 ; atomicité nonce/reçu renforcée en Mission 59).
- [x] Imposer l'append-only du registre local des reçus par triggers SQLite et ajouter un audit en lecture seule des digests SHA-256, du JSON canonique et des identifiants liés (Mission 60 ; intégrité locale, sans prétention d'inviolabilité).
- [x] Ajouter un checkpoint local du registre des reçus, signé Ed25519, liant le nombre d'enregistrements à une empreinte SHA-256 déterministe et détectant toute divergence ultérieure (Mission 61 ; vérification sans consommation de nonce ni mutation du registre).
- [x] Archiver durablement les checkpoints Ed25519 dans une base SQLite distincte, append-only, idempotente et auditable en lecture seule, avec vérification historique des signatures (Mission 62 ; sans réseau ni modification du registre métier).
- [x] Conserver les anciennes clés publiques versionnées lors des rotations et permettre la vérification cryptographique des archives après rotation/révocation, sans autorisation d’action ni consommation de nonce (Mission 63 ; audit uniquement).
- [x] Ajouter un journal transactionnel durable pour la rotation Ed25519, récupération fail-closed des états interrompus et reprise avant signature/nouvelle rotation (Mission 64 ; tests de panne simulée, sans réseau ni activation).
- [x] Ajouter un gestionnaire transactionnel central du cycle de vie des identités : provision, rotation, permissions et révocation, avec approbation explicite, idempotence, contrôle de révision, journal append-only et chaîne SHA-256 (Mission 65 ; CI verte sur le SHA final, aucune activation réelle).
- [x] Ajouter un moteur de rapprochement en lecture seule entre registre canonique et journal transactionnel : détection des identités orphelines, activations non autorisées, écarts d'état/permissions, révisions et versions de clés invalides ; rapport déterministe SHA-256 et recommandation fail-closed (Mission 66 ; CI verte sur le SHA final, aucune correction automatique ni activation).
- [x] Ajouter des adaptateurs locaux read-only pour extraire le registre JSON canonique et le ledger SQLite, valider les schémas, refuser les sources ambiguës et alimenter directement le moteur de rapprochement (Mission 67 ; CI verte sur le SHA final, aucune écriture, aucun accès réseau).
- [x] Durcir les adaptateurs de snapshots : ouverture par descripteur sans suivi de lien symbolique, limites de taille, détection des clés JSON dupliquées et validation stricte du ledger SQLite (Mission 68 ; CI verte sur le SHA final, aucune mutation ni accès réseau).
- [x] Ajouter un contrat sémantique commun aux snapshots : identifiants uniques, statuts bornés, permissions/interdictions cohérentes et versions strictement positives (Mission 69 ; CI verte sur le SHA validé, aucune mutation ni activation).
- [x] Rendre atomiques la réservation du nonce Ed25519 anti-rejeu et l'archivage du reçu de transport dans une seule transaction SQLite `BEGIN IMMEDIATE` / `COMMIT`, avec rollback conjoint et idempotence des doublons exacts (Mission 59 ; aucun réseau ni import).

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
- [ ] PAPI SOCIAL GROWTH : équipes distinctes par réseau, publication autorisée, audience réelle, prospection, opportunités rémunérées et suivi des conversions ; équipe de 10 agents d'analyse vidéo.
- [ ] Intégrer les prestataires de paiement après validation de l'éligibilité, des frais, des permissions et des conditions.
- [ ] Mettre en place sauvegardes, rapprochement périodique et séparation des rôles comptables.

## Mise en service
Un composant est opérationnel uniquement si code/configuration, accès autorisés, test reproductible, journaux et procédure d'arrêt sont présents.

## Statut
Fondations de code et documentation présentes. Le worker vérifie les identités Ed25519 en mode local par défaut, ou via un adaptateur Supabase explicitement injecté. Le schéma et l'adaptateur partagés sont codés et testés par simulation, mais aucun projet distant n'est configuré et aucune migration n'est exécutée. Aucun agent autonome, worker permanent, scheduler déployé, boutique, prospection externe ou paiement automatisé n'est actif. Aucun modèle IA n'est connecté à ce stade.



## État des missions récentes
- Mission 65 : CI confirmée verte sur le SHA final ; PR #227 toujours en brouillon, non fusionnée.
- Mission 66 : CI confirmée verte sur le SHA final `641627a86825e48e9aeba03b51b85a3186aea4cb` ; PR #228 toujours en brouillon, non fusionnée.
- Mission 67 : adaptateurs d'extraction locale en lecture seule ; CI verte sur le SHA final cb0ad31e1c46e4c9503ab70184f66c824da58188 ; PR #229 toujours en brouillon, non fusionnée.
- Mission 68 : durcissement des entrées de snapshots JSON/SQLite ; CI verte sur le SHA final `19f6be2efa7c79800e23b9d8ba79d392832d564f` ; PR #230 toujours en brouillon, non fusionnée.
- Mission 69 : contrat sémantique des snapshots d'identité ; CI verte sur le SHA `e332b945834e20787fda77b1fc9a8f4b41fe21ea` (run `43655388046`) ; PR #231 toujours en brouillon, non fusionnée.
