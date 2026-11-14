# Mission 40 — Procédure opérateur

## Préconditions
- Utiliser une identité propriétaire active du registre Ed25519 local.
- Garder la clé privée sur le poste autorisé, avec permissions restrictives.
- Vérifier l'horloge système et l'identité de destination attendue.
- Construire le paquet avec le validateur de Mission 39.

## Contrôle
Le signataire crée une attestation via `sign_sync_bundle_approval`; le destinataire la vérifie via `verify_sync_bundle_approval`, avec registre public, base SQLite anti-rejeu et destination attendue explicite.

Tout échec est bloquant. Une approbation n'est valable que pour le digest, l'origine, la destination, l'export et l'ordre des événements signés. La durée maximale par défaut est de 900 secondes.

## Sécurité et limites
Ne jamais transmettre ni commiter la clé privée. La base SQLite de rejeu est locale : sauvegarde, concurrence multi-instance et réplication ne sont pas garanties. La validation n'importe aucun contenu et n'écrit aucune donnée métier. L'approbation n'est pas consommée dans le ledger SQL partagé; toute future importation nécessitera une consommation atomique et durable, puis une transaction d'import distincte.

## Arrêt d'urgence
En cas de clé compromise, révoquer l'identité dans le registre local, arrêter toute opération en cours et renouveler la clé selon la procédure Ed25519 existante. Ne pas contourner un refus ou réutiliser un nonce.
