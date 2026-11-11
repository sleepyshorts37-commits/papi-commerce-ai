# PAPI COMMERCE AI

Groupe commercial numérique assisté par agents IA. **État : fondations techniques ; aucun agent autonome n'est encore déployé.**

## Activités prévues
1. **PAPI MARKET** — vente de produits finis.
2. **PAPI DROPSHIPPING** — vente avec expédition par fournisseur.
3. **PAPI AFFILIATION** — affiliation et parrainages autorisés.
4. **PAPI FREELANCE** — missions réalisables et autorisées pour des agents IA.
5. **PAPI SERVICES** — services numériques aux entreprises.
6. **PAPI BUSINESS PARTNERS** — apport d'affaires rémunéré à la commission.

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

## Commandes locales
Depuis la racine du dépôt :
- `PYTHONPATH=runtime python -m papi_core validate` — valider les registres.
- `PYTHONPATH=runtime python -m papi_core doctor` — vérifier la présence des variables Supabase sans afficher leurs valeurs ni effectuer de connexion réseau.
- `PYTHONPATH=runtime python -m papi_core dashboard` — afficher le tableau de bord en lecture seule.
- `PYTHONPATH=runtime python -m papi_core schedule-preview` — calculer les échéances récurrentes à examiner, sans exécuter de tâche.
- `PYTHONPATH=runtime python -m papi_core sales-validate` — valider les registres commerciaux locaux.
- `PYTHONPATH=runtime python -m papi_core sales-report` — afficher les indicateurs commerciaux locaux, sans action externe.
- `PYTHONPATH=runtime python -m papi_core finance-validate` — valider le registre financier local.
- `PYTHONPATH=runtime python -m papi_core finance-report` — afficher les recettes vérifiées et dépenses payées, en lecture seule.

Le worker reste désactivé par défaut. Le planificateur ne démarre aucun processus permanent et n'enfile aucun travail.

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
- [Préparation de l'environnement Supabase](docs/ENVIRONMENT-SETUP.md)

GitHub héberge le code et les documents ; il ne fait pas fonctionner à lui seul des agents en continu. L'orchestration, l'hébergement, les connexions et les tâches planifiées restent à déployer et tester.
