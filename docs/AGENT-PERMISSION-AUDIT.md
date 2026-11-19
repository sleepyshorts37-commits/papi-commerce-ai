# Audit local des permissions des agents

## Commande

Depuis la racine du dépôt :

```sh
PYTHONPATH=runtime python -m papi_core agent-permission-report
```

Pour auditer des registres de test :

```sh
PYTHONPATH=runtime python -m papi_core agent-permission-report --agents /tmp/agents.json --policy /tmp/policy.json
```

La commande produit un rapport JSON en lecture seule. Elle ne modifie aucun registre, ne contacte aucun service et n'authentifie aucun processus.

## Trois niveaux distincts

- **Déclaration** : permission présente dans `data/agents.json`, interdiction explicite et statut du rôle.
- **Contrôle local** : résultat de `authorize_agent` sur le profil et la politique fournis. Un résultat `allow` signifie seulement que ce contrôle local accepte la déclaration.
- **Barrière runtime** : reste `blocked` dans ce scaffold. L'exécution globale est désactivée ; les signatures, l'identité du worker, la tâche, le handler, les approbations et l'environnement de déploiement ne sont pas validés par ce rapport.

Le rapport n'authentifie jamais un agent, ne prouve pas qu'il est déployé et n'accorde aucune permission.

## Refus par défaut

Le rapport est marqué `blocked` si le registre ou la politique est illisible/invalide, si une permission n'est pas un identifiant ASCII minuscule valide, si des déclarations sont dupliquées ou si une permission est à la fois déclarée et interdite. Les politiques qui ne satisfont pas les garde-fous de sécurité locaux échouent également en mode fermé.

## Champs de sortie

- `status` : `ok` ou `blocked` pour la qualité du registre et de la politique, pas pour la disponibilité runtime.
- `local_check` : `allow` ou `deny` du contrôle local.
- `runtime_gate` : `blocked` ; les bloqueurs expliquent pourquoi.
- `runtime_execution_available`, `identity_authenticated`, `handler_execution_verified` : toujours `false` dans ce rapport.
- `summary` : comptes de rôles, déclarations, contrôles locaux et permissions non exécutables.

## État

Fonction locale testée par CI. Les agents du registre restent définis/planifiés ; aucun agent, worker, scheduler ou handler externe n'est activé. Le rapport ne remplace pas la revue de politique, l'authentification cryptographique, les tests de worker ou une revue indépendante de sécurité.
