# Mission 137 — Stockage privé et registre des illustrations

## Livrables
- Migration 014 : registre PostgreSQL des images, versions, empreintes, dimensions, fournisseur/modèle, statut de revue et journal d'audit.
- RLS activé ; accès réservé au backend/service_role ; aucun accès direct client.
- Module de stockage privé des illustrations PNG/JPEG/WebP avec validation des signatures et dimensions, taille limitée à 20 Mio, empreinte SHA-256 et écriture atomique.
- Versions par page ; même contenu/version idempotent ; remplacement silencieux d'une version existante interdit.
- Enregistrement PostgreSQL injectable ; en cas d'indisponibilité, fichier conservé et statut pending_retry pour reprise.
- Validation humaine obligatoire avant approbation ; les images reçues ne sont jamais considérées comme approuvées.
- Tests hors réseau pour formats, dimensions, sécurité du stockage, idempotence et reprise DB.

## Limites
- Ce service stocke des images déjà générées ; il ne déclenche pas de fournisseur.
- Le schéma et le code restent proposés en PR ; aucune migration active ni aucun déploiement.
- Aucune image réelle n'a été générée ni validée.
