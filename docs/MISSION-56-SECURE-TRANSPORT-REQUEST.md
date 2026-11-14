# Mission 56 — Construction de requête de transport sécurisée

## Objectif
Préparer un format de requête sortante déterministe pour transmettre un paquet .papisync et sa charge utile .papidata à une instance de destination, sans ouvrir de connexion réseau.

## Contrôles locaux
- Revalider les octets du paquet et de la charge utile contre le manifeste avant construction.
- Encoder les deux fichiers en Base64 dans un corps JSON canonique lié au delivery_id.
- Construire une requête POST avec une clé d'idempotence égale au delivery_id.
- Exiger HTTPS, port 443, hôte explicitement autorisé, sans identifiants, query ni fragment.
- Refuser IP non publiques, localhost et suffixes d'hôtes locaux/réservés.
- Retourner SHA-256 et taille du corps pour audit avant émission.

## Frontière de sécurité
Ce module ne fait aucun appel réseau, ne résout pas le DNS et ne vérifie pas à lui seul l'adresse IP réellement résolue. Le futur adaptateur d'émission devra imposer TLS avec validation de certificat, désactiver les redirections, contrôler l'adresse IP après résolution pour bloquer toute adresse non publique et toute réorientation DNS, appliquer délais/limites de taille, authentifier le destinataire et vérifier le reçu signé. Le serveur destinataire doit revalider le manifeste, les octets, la signature Ed25519, la destination et l'anti-rejeu atomique.

Aucun nonce n'est consommé, aucun reçu n'est créé, aucun contenu n'est importé. La requête préparée contient les données encodées : elle doit être traitée comme sensible et ne jamais être journalisée en clair.

## Tests
Tests de construction déterministe, décodage exact des fichiers, idempotence, refus HTTP/hôte non autorisé, hôtes locaux/IP privées, credentials/query/fragment/port non standard et fichiers modifiés.

## Hors périmètre
Aucun réseau, DNS, transfert réel, Supabase distant, Vercel, worker, scheduler, import ou déploiement.
