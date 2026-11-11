# Identité et contrôle d'accès local des agents

## Fonctionnement livré
- Chaque demande de contrôle référence un identifiant d'agent du registre.
- Le statut doit être exactement `active` ; `defined` et `planned` sont refusés.
- La capacité demandée doit figurer dans `permissions`.
- Une interdiction explicite prévaut toujours sur une permission.
- Les actions financières, juridiques et externes restent bloquées par la politique globale.
- Les actions réservées au propriétaire ne peuvent jamais être accordées à un agent.

## Limite de sécurité importante
Ce module est un **contrôle d'autorisation local**, pas une authentification d'identité. L'identifiant transmis par un processus n'est pas une preuve cryptographique de son identité. Aucun mot de passe, token ou secret partagé n'est créé ou stocké. Avant le déploiement multi-instance, ajouter une identité de service vérifiable (par exemple jetons courts signés ou identité de workload), une rotation, une révocation et des journaux d'audit. Les clés devront rester dans un gestionnaire de secrets, jamais dans le dépôt.

## Test
`PYTHONPATH=runtime python -m unittest discover -s tests -p 'test_authz.py' -v`

## État
Aucun agent du registre n'est activé par ce changement. Aucun accès externe n'est ouvert et aucune action n'est exécutée.
