# PAPI CHAT — socle local 0.4

PAPI CHAT est une messagerie interne locale. Elle ne contacte aucun service externe et ne prouve pas qu'un agent IA autonome est en fonctionnement.

## API Python

Chaque expéditeur doit posséder une clé privée Ed25519 provisionnée dans le répertoire local sécurisé. Le registre public doit contenir sa clé publique active.

```python
from papi_core.chat import send_message, read_messages

send_message(
    sender="astou",
    recipient="marietou",
    subject="Revue des priorités",
    body="Merci de vérifier les missions en attente.",
    # Par défaut : ~/.papi/identity/ed25519/astou.ed25519.pem
)
messages = read_messages(recipient="marietou", limit=50)
```

Les chemins de clés, du registre public et de la base anti-rejeu peuvent être injectés explicitement pour les tests et les environnements isolés. Les types de messages autorisés sont `info`, `task`, `alert`, `report`. Le destinataire `all` permet une diffusion interne.

## Authentification et intégrité

- Le contenu complet (identifiant, date, expéditeur, destinataire, sujet, corps et type) est signé par la clé privée Ed25519 de l'expéditeur.
- À l'envoi, le système vérifie la signature contre le registre public, exige une identité active et la version de clé courante, impose une fenêtre temporelle de cinq minutes et consomme le nonce dans la base anti-rejeu.
- À chaque lecture, la signature est vérifiée de nouveau sans consommer le nonce et sans imposer une nouvelle fenêtre de cinq minutes. Les lectures répétées ne sont donc pas considérées comme des rejeux.
- Une modification du contenu, de l'identité déclarée ou de la preuve est rejetée.
- Les nouvelles signatures exigent toujours la clé active et la version courante. Une clé historique ne peut jamais authentifier une nouvelle requête.
- Le registre conserve les clés publiques de chaque version avec leur période d'activation, de rotation ou de révocation. Les messages signés pendant cette période restent vérifiables après rotation/révocation ; les signatures horodatées après la fin de validité sont rejetées.
- Pour les anciens registres sans historique, une migration rétrocompatible conserve la clé publique courante comme version historique avec une date d'activation inconnue (borne initiale ouverte).
- Les messages non signés ne sont pas acceptés par cette API.

## Limites de sécurité

- Stockage append-only local dans `data/chat/messages.jsonl`, avec permissions de fichier restrictives. Ce n'est pas un stockage inviolable : un administrateur du système de fichiers peut modifier ou supprimer le journal.
- Les clés privées restent locales ; elles ne doivent jamais être ajoutées au dépôt Git, au journal de messages ou à un ticket.
- Le registre public doit être protégé contre les modifications non autorisées. La confiance dans une clé publique dépend de l'intégrité de ce registre.
- Pas de chiffrement du corps des messages, pas de synchronisation multi-serveur, pas de transport réseau et pas de notification externe.
- Les agents doivent disposer d'un environnement d'exécution sécurisé et de clés propres. La présence d'une clé ne signifie pas qu'un agent autonome est déployé.
- Ne pas y déposer de données personnelles sensibles, de mots de passe, de jetons ou d'informations financières confidentielles.

Avant tout déploiement multi-utilisateur, ajouter un historique de clés publiques immuable, un stockage serveur contrôlé, des autorisations par canal, du chiffrement en transit et au repos, une politique de rétention et une revue de sécurité.
