# PAPI COMMERCE AI

Groupe commercial numérique assisté par agents IA. **État : fondations techniques ; aucun agent autonome n'est encore déployé.**

## Activités prévues
1. **PAPI MARKET** — vente de produits finis.
2. **PAPI DROPSHIPPING** — vente avec expédition par fournisseur.
3. **PAPI AFFILIATION** — affiliation et parrainages autorisés.
4. **PAPI FREELANCE / GLOBAL WORK** — missions internationales accessibles et réalisables dans le respect des règles des plateformes.
5. **PAPI SERVICES** — services numériques aux entreprises.
6. **PAPI BUSINESS PARTNERS** — apport d'affaires rémunéré à la commission.
7. **PAPI SOCIAL GROWTH** — publications, croissance d'audience réelle, prospection, recherche de missions et ventes sur les pages officielles.
8. **PAPI VIDEO TASKS** — soumission de liens YouTube par le propriétaire et analyse de contenu par une équipe spécialisée.

## Principes
- Objectif initial : 0 FCFA. Aucune dépense, souscription, publicité payante ou crédit API sans autorisation explicite.
- Respect des lois, contrats, conditions des plateformes, règles anti-spam et protection des données.
- Aucun faux compte, fausse identité, faux avis, fausse vente ou conversion artificielle.
- Aucun mot de passe, token, OTP, PIN, CVV ou secret dans ce dépôt public.
- Revenus comptabilisés uniquement après vérification du paiement.
- Aucun retrait, transfert ou paiement par un agent sans autorisation.
- Une capacité n'est déclarée opérationnelle qu'après implémentation et test concluant.

## Architecture
Astou (coordination), Marietou Diouf (direction générale), Ibrahima (architecture des agents), Cheikh Fall (fiabilité), Aminou (alternatives), PAPI CHAT (communication interne), PAPI COMMAND CENTER (suivi), mémoire partagée locale et planificateur déterministe.

## Capacités préparées dans cette branche
- [PAPI GLOBAL WORK](docs/PAPI-GLOBAL-WORK-VIDEO-SOCIAL-GUIDE.md#1-papi-global-work) — évaluation locale de missions, pays, coûts, règles IA et automatisation.
- [PAPI SOCIAL GROWTH](docs/PAPI-GLOBAL-WORK-VIDEO-SOCIAL-GUIDE.md#2-papi-social-growth) — responsabilités combinées de publication, audience, prospection, missions et ventes.
- [PAPI VIDEO TASKS](docs/PAPI-GLOBAL-WORK-VIDEO-SOCIAL-GUIDE.md#3-papi-video-tasks) — validation d'un lien YouTube et création de dix tâches d'analyse.
- [Plan de mission 16](docs/PAPI-GLOBAL-WORK-VIDEO-SOCIAL-5-DAYS.md) et [rapport](docs/PAPI-GLOBAL-WORK-VIDEO-SOCIAL-REPORT.md).

## Commandes locales
Depuis la racine du dépôt :
- `PYTHONPATH=runtime python -m papi_core validate` — valider les registres agents et tâches.
- `PYTHONPATH=runtime python -m papi_core doctor` — vérifier la présence des variables Supabase sans afficher leurs valeurs ni effectuer de connexion réseau.
- `PYTHONPATH=runtime python -m papi_core dashboard` — afficher le tableau de bord en lecture seule.
- `PYTHONPATH=runtime python -m papi_core schedule-preview` — calculer les échéances récurrentes à examiner, sans exécuter de tâche.
- `PYTHONPATH=runtime python -m papi_core sales-validate` — valider les registres commerciaux locaux.
- `PYTHONPATH=runtime python -m papi_core sales-report` — afficher les indicateurs commerciaux locaux, sans action externe.
- `PYTHONPATH=runtime python -m papi_core finance-validate` — valider le registre financier local.
- `PYTHONPATH=runtime python -m papi_core finance-report` — afficher les recettes vérifiées et dépenses payées, en lecture seule.
- `PYTHONPATH=runtime python -m papi_core security-check` — contrôler les garde-fous locaux sans réseau ni affichage de secrets.

Le worker reste désactivé par défaut. Le planificateur ne démarre aucun processus permanent et n'enfile aucun travail.

## WEB BUILDER
- [Modèles sectoriels](docs/PAPI-SECTOR-BLUEPRINTS-GUIDE.md) — six plans sectoriels avec contrôle de complétude des informations, sans vérification automatique de leur véracité.

## Documents
- [Organisation](docs/ORGANISATION.md)
- [Gouvernance et sécurité](docs/GOUVERNANCE-SECURITE.md)
- [Architecture technique](docs/ARCHITECTURE.md)
- [Plan de réalisation](docs/ROADMAP.md)
- [Exploitation et gestion des tâches](docs/OPERATIONS.md)
- [Noyau de coordination](docs/CORE-ENGINE.md)
- [Orchestrateur consultatif](docs/ORCHESTRATOR.md)
- [Journal d'audit](docs/AUDIT-MEMORY.md)
- [Mémoire partagée](docs/SHARED-MEMORY.md)
- [Machine à états des missions](docs/STATE-MACHINE.md)
- [Persistance partagée Supabase](docs/SHARED-STORAGE.md)
- [File d'exécution et reprise](docs/EXECUTION-QUEUE.md)
- [Registre de handlers et permissions](docs/HANDLER-PERMISSIONS.md)
- [Worker contrôlé](docs/WORKER.md)
- [Planificateur](docs/SCHEDULER.md)
- [Outils commerciaux](docs/SALES-TOOLS.md)
- [Finances et comptabilité](docs/FINANCE-LEDGER.md)
- [Sécurité et préparation au déploiement](docs/SECURITY-RELEASE.md)
- [Préparation de l'environnement Supabase](docs/ENVIRONMENT-SETUP.md)

GitHub héberge le code et les documents ; il ne fait pas fonctionner à lui seul des agents en continu. L'orchestration, l'hébergement, les connexions et les tâches planifiées restent à déployer et tester.
