# Gestion des clés de signature des checkpoints d'audit

## Module local Ed25519

`papi_core.audit_anchor_keys.LocalAuditKeyring` fournit un magasin de clés de signature destiné uniquement à un backend de confiance :

- `provision()` crée la première clé Ed25519 ;
- `sign(key_id, message)` signe uniquement avec la clé active ;
- `rotate(current_key_id)` crée une nouvelle clé et conserve l'ancienne clé publique avec l'état `retired` ;
- `verify(key_id, message, signature)` vérifie les clés actives et retirées afin de préserver la vérifiabilité historique ;
- `revoke(key_id)` révoque immédiatement une clé ; une clé révoquée ne peut plus signer ni vérifier.

Le registre JSON ne contient que les clés publiques et les états. Les clés privées sont des fichiers PEM séparés non chiffrés par mot de passe, permissions 0600, dans un répertoire 0700 ; la confidentialité repose donc sur les permissions et la protection du système de fichiers. Le code vérifie également que la clé privée correspond à la clé publique enregistrée. Le registre et les clés sont créés localement ; aucun secret n'est ajouté au dépôt.

## Utilisation avec l'ancrage externe

Le contrat `SignatureVerifier` de `papi_core.audit_anchor` accepte directement `keyring.verify`. Pour créer une signature, l'appelant signe les octets canoniques sans le champ `signature` (même sérialisation déterministe que `_unsigned_payload`) puis ajoute la signature hexadécimale et le `key_id` au record.

Les clés retirées restent valides pour vérifier les anciennes entrées. Après révocation d'une clé compromise, `rotate(key_id)` permet de créer une nouvelle clé sans réactiver l'ancienne, à condition qu'aucune autre clé ne soit active. La révocation est volontairement plus forte que la rétention historique : elle invalide également la vérification des signatures anciennes faites avec la clé compromise. Une rotation ou révocation doit être auditée par le backend opérateur.

## Limites

Il s'agit d'un gestionnaire local de clés pour tests et déploiement contrôlé, pas d'un KMS/HSM, d'un coffre matériel ou d'une solution de gestion distribuée. Aucun mécanisme de synchronisation multi-instance ni de révocation transactionnelle distante n'est inclus. Les fichiers privés ne doivent jamais être copiés dans Git, transmis aux agents, ou exposés à une API publique. Les tests utilisent uniquement des clés éphémères générées en mémoire ou dans des répertoires temporaires.
