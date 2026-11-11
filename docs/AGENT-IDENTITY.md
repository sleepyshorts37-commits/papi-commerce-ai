# Authentification cryptographique des agents

## État de l'intégration
Le runtime prend en charge deux formats d'enveloppe pendant la migration :
- HMAC-SHA256 historique pour les enveloppes sans champ `key_version`.
- Ed25519 pour les enveloppes contenant `key_version`, vérifiées avec `papi_core.identity_ed25519`.

Le worker appelle `authorize_authenticated_agent` avant tout handler. Le contrôle lie strictement l'agent, la permission, le `task_id` et le nom du handler. La politique d'accès et le statut actif de l'agent sont vérifiés après l'authentification. Une signature valide ne donne donc pas, à elle seule, le droit d'exécuter une action.

## Ed25519 local
Le module `papi_core.identity_ed25519` fournit :
- génération d'une clé privée Ed25519 par agent ;
- stockage PEM local avec permissions restrictives ;
- publication de la seule clé publique dans un registre JSON versionné ;
- signatures sur l'identifiant, la version de clé, l'horodatage, le nonce et le payload ;
- vérification de signature, fenêtre temporelle de cinq minutes et anti-rejeu SQLite ;
- révocation et rotation de clé avec incrément de version.

Exemple :
```python
from papi_core.identity_ed25519 import (
    provision_ed25519_agent, sign_ed25519_request, verify_ed25519_request
)

private_path = provision_ed25519_agent("agent-id")
envelope = sign_ed25519_request(
    "agent-id",
    {"permission": "read_reports", "task_id": "task-id", "handler": "report.preview"},
    private_path,
)
verified = verify_ed25519_request(envelope)
```

La clé privée ne doit jamais être copiée dans GitHub, un dépôt public, un journal ou une conversation. Elle doit être créée et conservée uniquement dans l'environnement de confiance de l'agent.

## Intégration worker et file d'exécution
Chaque job doit transporter `agent_identity`, l'enveloppe signée. Le payload signé doit correspondre exactement à :
```json
{"permission":"read_reports","task_id":"task-id","handler":"report.preview"}
```
L'identifiant signé doit correspondre à `owner_agent` de la tâche. Le worker vérifie l'enveloppe avant d'appeler le handler. Une enveloppe absente, altérée, expirée, rejouée, révoquée ou liée à un autre job bloque le travail.

Le schéma Supabase ajoute `agent_identity` à `papi_jobs` et la réservation retourne cette propriété. Le script SQL doit être exécuté par le propriétaire dans le projet Supabase avant utilisation distante ; aucun projet distant n'a été modifié par les commits GitHub.

## Registre central et anti-rejeu partagé : schéma préparé
La migration SQL ajoute :
- `papi_agent_public_keys` : une clé publique par version et un seul enregistrement actif par agent ;
- `papi_agent_used_nonces` : unicité transactionnelle du couple agent/nonce ;
- `papi_consume_agent_nonce` : RPC atomique qui refuse un nonce déjà consommé et limite sa durée de validité.

Les tables sont privées aux rôles serveur. Aucune clé privée n'est stockée dans Supabase. Les workers ne doivent jamais recevoir une clé `service_role) dans le navigateur ou dans un dépôt. Le backend serveur doit vérifier l'état et la version de la clé publique, puis consommer le nonce via la RPC.

**Limite actuelle :** le runtime utilise encore le registre JSON et SQLite locaux par défaut. Le schéma partagé est préparé, mais aucun adaptateur Supabase n'est encore implémenté, aucune migration distante n'a été exécutée et la révocation/anti-rejeu multi-instance ne sont donc pas opérationnels.

## Révocation et rotation
- La révocation marque une identité comme révoquée ; les vérificateurs doivent refuser toute version révoquée.
- La rotation incrémente la version et rend les anciennes enveloppes invalides.
- En environnement distribué, la mise à jour du registre et le changement de version doivent être atomiques et audités.
- Après compromission, arrêter l'agent, révoquer sa clé, provisionner une nouvelle clé sur son environnement de confiance et vérifier la nouvelle identité avant reprise.

## Tests et sécurité
Les tests unitaires couvrent signatures valides/invalides, liaison au job, expiration, rejeu, rotation et révocation. La CI valide le code ; elle ne remplace pas un test d'intégration Supabase, une revue indépendante ni un test d'intrusion.

Aucun agent n'est activé, aucun worker permanent n'est déployé, aucune action externe ou financière n'est autorisée et aucun modèle IA n'est connecté.
