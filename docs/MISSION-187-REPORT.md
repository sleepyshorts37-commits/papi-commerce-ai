# Mission 187 — Audit local des permissions des agents

## Objectif
Fournir une vue en lecture seule des permissions déclarées dans le registre agents, du résultat du contrôle local et des blocages runtime connus, sans activer de rôle ni exécuter d'action.

## Changements
- Ajout de `runtime/papi_core/agent_permission_report.py` : rapport par agent et permission, avec statut, interdictions, résultat du contrôle local et bloqueurs runtime.
- Distinction explicite entre déclaration, autorisation locale et disponibilité runtime.
- Refus par défaut si le registre ou la politique est invalide, si une permission est mal formée, dupliquée ou également interdite.
- Ajout de la commande `agent-permission-report`, avec chemins de registres optionnels pour les tests.
- Ajout de 12 tests couvrant contrôle local permis, rôle planifié, interdiction explicite, permission owner-only, action externe, registre malformé, token invalide, doublons/chevauchement, politique invalide, fichiers absents, registre réel et CLI.
- Mise à jour README, roadmap et documentation de la commande.
- CI registry check inclut maintenant `config/policy.json` dans les JSON vérifiés ; documentation check exige les deux nouveaux documents.

## Vérification CI sur SHA `dccd5194e1c4eceb57a83a0c99facc32e56e093c`
- [PAPI core tests — run #2836](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44491864841) : **succès, 224 tests**, dont les 12 nouveaux tests ; validation des registres et tests PostgreSQL jetable/anti-rejeu réussis.
- [PAPI registry validation — run #896](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44491864715) : **succès**, JSON de la politique inclus.
- [PAPI documentation checks — run #833](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44491864708) : **succès**.

Aucun test local n'a été exécuté dans cette session.

## Limites
- La commande n'authentifie pas les agents ; `identity_authenticated=false`.
- Un résultat local `allow` ne signifie pas que le handler, la tâche, l'approbation, la signature ou le worker sont valides.
- L'exécution reste désactivée ; `runtime_gate=blocked` pour chaque déclaration.
- Aucun agent activé, aucune action externe, aucun compte, secret, dépense ou déploiement.

## Gouvernance
PR brouillon vers `main`, non fusionnée. Aucune activation ou modification de permission n'a été effectuée.
