# Authentification cryptographique des agents

## Version locale livrée
Le module `papi_core.identity` ajoute une preuve cryptographique par agent avec HMAC-SHA256 :
- clé aléatoire individuelle de 256 bits, créée localement ;
- clé privée stockée sous `~/.papi/identity/keys/`, permissions fichier 0600 et dossier 0700 ;
- signature liée à l'identifiant, au contenu, à l'horodatage et à un nonce ;
- fenêtre temporelle maximale de cinq minutes ;
- registre SQLite des nonces consommés pour bloquer les rejeux, avec contrainte d'unicité ;
- comparaison de signature en temps constant.

## Utilisation locale
```python
from pathlib import Path
from papi_core.identity import provision_agent_key, sign_request, verify_request

key = provision_agent_key("agent-id")
envelope = sign_request("agent-id", {"operation": "read_only"}, key)
identity = verify_request(envelope)
```

La clé est créée sur la machine locale. Ne jamais la copier dans GitHub, un dépôt public, un journal ou une conversation. La création de clé ne doit être effectuée que sur l'environnement de confiance de l'agent. La perte ou compromission d'une clé exige révocation et rotation manuelles.

## Limites et sécurité
HMAC est un mécanisme à secret partagé : chaque vérificateur qui détient la clé peut aussi signer comme l'agent. Ce socle est adapté à un prototype local mono-hôte, pas à une architecture distribuée multi-hôte. Avant production, migrer vers Ed25519 ou une identité de workload avec clés privées non exportables, registre de clés publiques, révocation, rotation, synchronisation d'horloge et audit indépendant.

L'authentification prouve la possession de la clé, pas l'autorisation métier. Il faut toujours appeler séparément le contrôle d'accès `authorize_agent`, vérifier le statut du registre et appliquer la politique globale. Aucune clé n'est provisionnée dans le dépôt et aucun agent n'est activé par ce module.

## Tests
```bash
PYTHONPATH=runtime python -m unittest discover -s tests -p 'test_identity.py' -v
```

## État
Prototype cryptographique local livré. Pas de déploiement, pas de connexion multi-instance, pas d'action externe et aucun modèle IA connecté.
