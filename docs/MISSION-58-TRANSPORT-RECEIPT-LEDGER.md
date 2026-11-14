# Mission 58 — Registre local des reçus de transport

## Livrable
Un registre SQLite local append-only conserve les reçus de transport Ed25519 après vérification. Il indexe receipt_id et delivery_id, garde l'enveloppe canonique et son SHA-256, ainsi que les identifiants source/destination et le digest de la requête.

## Garanties
- Signature, identité destinataire, livraison et digests vérifiés par le validateur de Mission 57 avant insertion.
- Idempotence pour la répétition exacte d'un reçu déjà archivé.
- Refus d'un second reçu divergent pour la même livraison ou d'une collision d'identifiant.
- Transaction SQLite pour l'insertion, contraintes d'unicité et permissions de fichier restrictives.
- Aucun transfert réseau, import de données ou lancement d'agent.

## Limite importante
Le registre anti-rejeu Ed25519 et le registre métier de reçus sont deux bases SQLite distinctes. La consommation du nonce et l'archivage métier ne constituent donc pas une transaction distribuée atomique. Si le processus s'arrête après consommation du nonce et avant insertion, une réconciliation manuelle est nécessaire. Cette mission ne prétend pas résoudre cette fenêtre de panne.

## Tests
Insertion d'un reçu valide, répétition exacte idempotente, conflit de livraison, signature/décision invalide et requête altérée.
