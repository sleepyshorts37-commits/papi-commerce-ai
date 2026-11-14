# Mission 57 — Vérification du reçu de transport signé

## Objectif
Définir et vérifier localement le reçu cryptographique attendu après une transmission, sans effectuer de connexion réseau.

## Contrat du reçu
- Enveloppe Ed25519 émise par l'identité de l'instance destinataire.
- Portée `papi.sync.transport-receipt`, décision `accepted`, identifiant de reçu.
- Liaison stricte à `delivery_id`, digest SHA-256 du corps exact de la requête, source, destination, digest du paquet et digest de la charge utile.
- Vérification de la clé publique active, de sa version, de la signature, de l'horodatage et de l'anti-rejeu.
- Le nonce du reçu n'est consommé qu'après vérification de la signature et de toutes les liaisons au transfert.

## Frontière de sécurité
Ce module ne prouve pas qu'une requête a réellement été envoyée : il valide seulement un reçu présenté localement. Il n'ouvre aucune connexion, ne contacte aucun service, ne crée pas de reçu de transfert dans le registre métier, n'importe aucun contenu et n'active aucun agent. Le transport réel exigera encore une revue indépendante, une résolution DNS protégée contre le rebinding, TLS strict, limites/timeout, gestion des erreurs et validation côté destinataire.

## Tests
Signature destinataire correcte, mauvais signataire, mauvais delivery_id, corps altéré, digest de charge utile divergent, décision refusée et rejeu du nonce.
