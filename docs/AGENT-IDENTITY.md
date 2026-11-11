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


## Intégration contrôle d'accès et file d'exécution

Chaque job doit transporter une propriété `agent_identity` contenant l'enveloppe signée. Le payload signé doit correspondre exactement à :
```json
{"permission":"read_reports","task_id":"task-id","handler":"report.preview"}
```
L'identifiant dans l'enveloppe doit être identique à `owner_agent` de la tâche. Le worker vérifie la signature et le nonce, puis vérifie le statut actif, la permission du registre et la politique globale avant d'appeler le handler. Une enveloppe absente, altérée, expirée, rejouée ou liée à un autre job bloque le travail et le marque en échec contrôlé.

La table `papi_jobs` possède la colonne JSONB `agent_identity`; la fonction RPC de réservation la retourne au worker. La migration SQL ajoute cette colonne de manière compatible avec une table existante. Il faut réexécuter le script SQL dans le projet Supabase par le propriétaire avant d'utiliser cette évolution. Aucun projet distant n'a été modifié par le commit GitHub.

Les classes de handler sont associées à une permission explicite :
- `read_only` → `read_reports`
- `internal_write` → `update_internal_state`
- `external_communication` → `send_message`
- `financial` → `make_payment`
- `legal` → `accept_legal_commitments`

Ces permissions ne remplacent pas les validations de la politique globale ni les approbations du propriétaire. Les actions externes, financières et juridiques restent désactivées dans la configuration actuelle.


## Révocation et rotation locales

- `revoke_agent_key(agent_id)` inscrit l'identité dans `~/.papi/identity/revocations.json` ; toute vérification ultérieure échoue en mode fermé.
- `rotate_agent_key(agent_id)` remplace la clé par 32 octets aléatoires via un remplacement atomique. Les signatures de l'ancienne clé deviennent invalides.
- Le registre de révocation et les clés restent locaux, hors dépôt, avec permissions restrictives.
- La rotation doit être coordonnée : arrêter l'agent, révoquer, remplacer la clé, provisionner le nouveau secret uniquement dans l'environnement de confiance, puis reprendre après test.
- Une rotation locale ne distribue pas automatiquement la nouvelle clé aux autres machines. Le registre JSON local n'est pas un service de révocation distribué.

## Préparation multi-instance

Le HMAC actuel et SQLite anti-rejeu restent mono-hôte. Avant d'autoriser plusieurs instances, migrer vers Ed25519 (clés privées détenues par chaque agent, clés publiques côté vérificateur), registre central de clés versionnées et révocables, stockage anti-rejeu transactionnel partagé, horloges synchronisées et audit central append-only. Les instances doivent refuser toute identité inconnue, révoquée ou dont la version de clé n'est pas active. Aucun secret partagé ne doit être distribué entre workers.


## Prototype Ed25519 (socle de migration)

Le module `papi_core.identity_ed25519` introduit des signatures asymétriques :
- la clé privée Ed25519 reste sur l'environnement de l'agent, fichier PEM local avec permissions 0600 ;
- seul le matériel public est inscrit dans un registre JSON local versionné ;
- chaque enveloppe signe l'identifiant, la version de clé, l'horodatage, le nonce et le payload ;
- le vérificateur refuse les identités révoquées, les versions obsolètes, les signatures invalides, expirées ou rejouées ;
- la rotation incrémente la version et invalide les anciennes signatures ; la révocation bloque l'identité.

Dépendance : `cryptography` (voir `requirements.txt`). Les tests CI l'installent explicitement.

**Limite importante :** le registre JSON et la base SQLite anti-rejeu sont encore locaux à une machine. Ce module n'est pas encore branché au worker HMAC existant et ne fournit pas de révocation ou d'anti-rejeu entre plusieurs hôtes. Ne pas l'utiliser pour déclarer un déploiement multi-instance opérationnel. La prochaine étape est un backend transactionnel partagé, puis une migration contrôlée du worker et des jobs vers les enveloppes Ed25519.
