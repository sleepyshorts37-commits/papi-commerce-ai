# Mission 63 — Conservation des clés publiques historiques

## Objectif
Garantir l'auditabilité cryptographique des checkpoints archivés après rotation ou révocation d'une clé Ed25519, sans réactiver une ancienne clé pour authentifier des actions.

## Fonctionnement
- Lors d'une rotation, déplacer la clé publique courante dans un historique versionné avec sa date de retrait.
- Valider le type exact des versions (entiers, jamais booléens), l'unicité et l'ordre croissant des versions, ainsi que le format hexadécimal et la longueur de 32 octets de chaque clé publique.
- Valider l'historique avant de remplacer le fichier de clé privée ; un historique mal formé doit laisser la clé privée et le registre inchangés.
- Conserver les clés publiques courantes et anciennes dans le registre local ; ne jamais y copier de clé privée.
- Ajouter une primitive dédiée à la vérification d'une signature archivée : aucune vérification de fraîcheur, aucune consommation de nonce et aucune autorisation d'exécution.
- Réserver la vérification normale des requêtes aux identités actives et à la version courante, avec expiration anti-rejeu inchangée et validation stricte du registre.
- Faire utiliser cette primitive dédiée par l'audit des checkpoints archivés.

## Tests
- Signature courante vérifiable en mode archive.
- Signature ancienne vérifiable après rotation.
- Signature vérifiable après révocation pour preuve historique uniquement.
- Ancienne clé toujours refusée par le chemin normal d'authentification.
- Falsification du payload ou de la signature rejetée.
- Versions booléennes, historiques désordonnés/invalides et clés publiques mal formées rejetés.
- Une rotation refusée pour historique invalide ne modifie pas le fichier de clé privée.
- Audit du checkpoint conservé après rotation et révocation.

## Limites
La conservation de clés publiques historiques prouve qu'une signature correspond à une clé connue du registre ; elle ne prouve pas à elle seule que la clé n'était pas compromise au moment de la signature. L'horodatage fiable et l'ancrage externe restent hors périmètre. Aucun réseau, déploiement, worker, scheduler, paiement ou contact externe n'est activé.
