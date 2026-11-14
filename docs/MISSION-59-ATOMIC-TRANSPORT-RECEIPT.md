# Mission 59 — Atomicité nonce anti-rejeu et reçu de transport

## Objectif
Supprimer la fenêtre de panne entre la consommation du nonce Ed25519 du destinataire et l'archivage du reçu de transport.

## Implémentation
- Le registre des nonces `used_nonces` et la table `sync_transport_receipts` résident désormais dans le même fichier SQLite.
- Le vérificateur Ed25519 expose une variante transactionnelle qui réserve le nonce sur la connexion SQLite fournie par l'appelant, sans ouvrir ni valider sa propre transaction.
- Le ledger ouvre une transaction `BEGIN IMMEDIATE`, contrôle les doublons, vérifie la signature et tous les liens du reçu, réserve le nonce, insère le reçu, puis valide une seule fois.
- Toute erreur avant le commit annule à la fois la réservation du nonce et l'insertion du reçu.
- Les appels qui fournissent deux chemins SQLite différents sont rejetés explicitement.
- Un reçu strictement identique reste idempotent et retourne `already_recorded` sans tenter de consommer une deuxième fois son nonce.
- Le mode de fichier SQLite est fixé à 0600 après un enregistrement réussi.

## Tests
- Enregistrement et nonce présents dans la même base.
- Répétition exacte idempotente.
- Collision de livraison rejetée.
- Signature invalide : aucune ligne de reçu ni nonce consommé.
- Requête altérée : aucune ligne de reçu ni nonce consommé.
- Bases de rejeu et de ledger séparées : rejet avant création de fichier.

## Limites et sécurité
Cette mission améliore l'atomicité locale SQLite uniquement. Elle n'ajoute aucun transport réseau, import de données, synchronisation multi-instance, worker, scheduler ni exécution autonome. Les chemins SQLite doivent être protégés contre les accès concurrents non autorisés et le stockage local doit être sauvegardé. Aucun secret ni donnée client n'est ajouté au dépôt.
