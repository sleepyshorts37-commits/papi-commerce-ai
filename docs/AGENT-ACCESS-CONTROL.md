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


## Liaison cryptographique à un service destinataire

Les appels interservices peuvent utiliser `authorize_service_agent`, une frontière stricte qui exige une audience et un identifiant de service non vides. Les deux valeurs doivent être présentes dans le payload signé Ed25519, en plus de `permission`, `task_id` et `handler`. Le vérificateur compare le payload signé à la cible attendue avant d'émettre le principal authentifié.

Exemple de payload signé :
```json
{"permission":"read_reports","task_id":"task-123","handler":"report.preview","audience":"papi-reporting","service_id":"reporting-api"}
```

Une enveloppe destinée à une autre audience ou à un autre service est refusée. L'ancienne fonction `authorize_authenticated_agent` conserve sa compatibilité pour les flux locaux existants ; pour les frontières interservices, les appelants doivent utiliser `authorize_service_agent`. Cette étape fournit le contrat d'autorisation et ses tests, pas un transport réseau, un fournisseur d'identité workload, ni une intégration de production.
