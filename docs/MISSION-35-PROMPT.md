# Mission 35 — PAPI ORGANIZATION & AGENT IDENTITY GOVERNANCE

## Périmètre
Mission de cinq journées, exécutée en une seule séquence de travail dans le dépôt GitHub. Objectif : fiabiliser l'organigramme et le registre canonique des agents, résoudre les divergences documentaires identifiées sans inventer d'identités ni modifier les missions.

## Jour 1 — Audit
- Comparer `data/agents.json`, `docs/ORGANISATION.md`, les fiches d'identité et les contrôles du registre.
- Distinguer les identifiants techniques des noms affichés.
- Vérifier les collisions après normalisation Unicode.
- Relever les divergences sans modifier arbitrairement les personnes ou les responsabilités.

## Jour 2 — Référentiel et règles
- Définir `data/agents.json` comme source canonique.
- Formaliser les règles d'unicité, de fonction, de département, de statut et de permissions.
- Vérifier les références hiérarchiques facultatives.
- Clarifier Ndeye/LinkedIn, Oumou/RH, Cheikh/e-mail et Cheikh Fall/fiabilité.

## Jour 3 — Implémentation
- Ajouter un validateur déterministe de l'annuaire.
- Normaliser les noms en Unicode, sans tenir compte des accents, de la casse ou des espaces.
- Refuser les IDs invalides/dupliqués, noms ambigus, champs requis absents, statuts inconnus, permissions/interdictions invalides ou managers inconnus.
- Produire un résumé sans donnée sensible.

## Jour 4 — Tests et intégration
- Ajouter tests positifs et négatifs.
- Ajouter la commande CLI `organization-check`.
- Faire échouer le code retour de la commande si le registre est invalide.
- Exécuter ce contrôle dans la CI.

## Jour 5 — Documentation et transfert
- Mettre à jour le document d'organisation et le README.
- Documenter les limites et la procédure de changement d'identité.
- Exécuter tous les tests et contrôles.
- Vérifier le SHA final exact et ouvrir une PR draft non fusionnée.

## Livrables
- Validateur dans `runtime/papi_core/registry.py`.
- Commande `organization-check`.
- Tests automatisés.
- CI renforcée.
- Documentation de gouvernance et rapport final.

## Gouvernance
Aucune création d'agent actif, aucune permission nouvelle, aucun contact externe, aucun déploiement, aucun coût et aucune action financière. Les PR précédentes restent ouvertes et non fusionnées.
