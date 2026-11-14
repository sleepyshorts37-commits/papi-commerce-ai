# Mission 61 — Checkpoint Ed25519 du registre des reçus

## Objectif
Fournir une preuve locale, signée par une identité Ed25519 active, de l'état exact du registre append-only des reçus à un instant donné.

## Implémentation
- Calcul d'une empreinte SHA-256 déterministe sur les enregistrements du registre, triés par receipt_id et incluant les champs persistés.
- Création d'un checkpoint versionné contenant le nombre de reçus et l'empreinte du registre.
- Signature du contenu avec une clé privée Ed25519 locale ; seule la clé publique déjà enregistrée est nécessaire à la vérification.
- Vérification de la signature, du schéma strict, de l'audit d'intégrité courant et de l'égalité exacte entre le registre actuel et le snapshot signé.
- Le vérificateur n'écrit pas dans SQLite et ne consomme pas de nonce ; la création ne modifie pas le registre.
- Tests couvrant la vérification nominale, l'ajout postérieur d'un reçu, la falsification de signature ou de contenu et les métadonnées d'action externe.

## Limites et sécurité
Le checkpoint détecte les changements du registre depuis sa signature, mais ne remplace pas une sauvegarde indépendante et ne protège pas contre la compromission simultanée de la clé privée et du checkpoint. La clé privée reste locale, hors du dépôt. L'horodatage dépend de l'horloge du signataire ; aucun service d'horodatage tiers n'est utilisé.

Aucun réseau, import, déploiement, worker, scheduler, publication, paiement ou contact externe n'est ajouté.
