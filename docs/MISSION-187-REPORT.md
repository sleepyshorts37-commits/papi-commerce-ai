# Mission 187 — Audit local des permissions des agents

## Objectif
Fournir une vue en lecture seule des permissions déclarées dans le registre agents, du résultat du contrôle local et des blocages runtime connus, sans activer de rôle ni exécuter d'action.

## Changements
- Ajout de `runtime/papi_core/agent_permission_report.py` : rapport par agent et permission, avec statut, interdictions, résultat du contrôle local et bloqueurs runtime.
- Distinction explicite entre déclaration, autorisation locale et disponibilité runtime.
- Refus par défaut si le registre ou la politique est invalide, si une permission est mal formée, dupliquée ou également interdite.
- Ajout de la commande `agent-permission-report`, avec chemins de registres optionnels pour les tests.
- Ajout de 10 tests couvrant contrôle local permis, rôle planifié, interdiction explicite, registre malformé, token invalide, doublons/chevauchement, politique invalide, fichiers absents, registre réel et CLI.
- Mise à jour README, roadmap et documentation de la commande.
- CI registry check inclut maintenant `config/policy.json` dans les JSON vérifiés ; documentation check exige le nouveau document.

## Limites
- La commande n'authentifie pas les agents ; `identity_authenticated=false`.
- Un résultat local `allow` ne signifie pas que le handler, la tâche, l'approbation, la signature ou le worker sont valides.
- L'exécution reste désactivée ; `runtime_gate=blocked` pour chaque déclaration.
- Aucun agent activé, aucune action externe, aucun compte, secret, dépense ou déploiement.

## Validation
Les workflows GitHub Actions de la PR doivent confirmer les tests Python, la validation du registre/politique JSON et la présence documentaire. Aucun test local n'est revendiqué dans cette session.
