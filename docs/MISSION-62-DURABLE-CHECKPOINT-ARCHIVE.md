# Mission 62 — Archive append-only des checkpoints signés

## Objectif
Conserver durablement les checkpoints Ed25519 de l'audit des reçus, dans une base SQLite locale distincte du registre métier.

## Fonctionnement
- Avant archivage, vérifier la signature et confirmer que le checkpoint correspond au registre actuel.
- Calculer un identifiant SHA-256 du JSON canonique complet et stocker l'enveloppe signée dans une archive SQLite séparée.
- Rendre l'archive append-only par triggers UPDATE/DELETE.
- Rendre les insertions atomiques et les doublons exacts idempotents ; refuser les collisions/contenus divergents.
- Auditer l'archive en lecture seule : canonicalisation JSON, digest, correspondance d'identifiant et vérification Ed25519 contre le registre public d'identités.
- Permettre l'audit historique d'un checkpoint même si le registre des reçus a évolué depuis sa création. Cet audit historique ne prétend pas que le snapshot reste l'état actuel du ledger.

## Sécurité et limites
Les clés privées ne sont jamais copiées dans l'archive ni dans GitHub. L'archive SQLite locale n'est pas inviolable contre un attaquant qui contrôle le fichier et peut modifier ses triggers ; le digest et la signature permettent de détecter les altérations sans clé privée. La sauvegarde indépendante de l'archive reste nécessaire.

Aucun réseau, import, déploiement, worker, scheduler, publication, paiement ou contact externe n'est activé.
