# PAPI CHAT — socle local 0.1

PAPI CHAT fournit une boîte de messages interne locale entre les identifiants du registre des agents, le propriétaire (`owner`) et le système (`system`).

## API Python

```python
from papi_core.chat import send_message, read_messages

send_message(
    sender="astou",
    recipient="marietou",
    subject="Revue des priorités",
    body="Merci de vérifier les missions en attente.",
    message_type="task",
)
messages = read_messages(recipient="marietou", limit=50)
```

Types autorisés : `info`, `task`, `alert`, `report`. Le destinataire `all` permet une diffusion interne.

## Sécurité

- Stockage append-only local dans `data/chat/messages.jsonl`, permissions de fichier restrictives.
- Identifiants expéditeur/destinataire vérifiés contre le registre.
- Taille du message limitée et détection de chaînes ressemblant à des secrets.
- Aucun appel réseau, email, WhatsApp, réseau social ou notification externe.
- Aucun modèle IA n'est connecté : un message écrit par un agent reste une donnée enregistrée, pas la preuve qu'un agent autonome a parlé.
- Pas de chiffrement ni de synchronisation multi-serveur dans cette version. Ne pas y déposer de données personnelles ou confidentielles.

Une future version serveur devra ajouter authentification, autorisations par canal, chiffrement en transit et au repos, rétention, contrôle d'accès et journalisation avant tout usage réel multi-utilisateur.
