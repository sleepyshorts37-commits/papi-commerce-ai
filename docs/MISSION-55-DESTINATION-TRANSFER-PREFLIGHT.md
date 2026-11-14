# Mission 55 — Précontrôle de transfert côté destination

## Objectif
Ajouter un précontrôle local en lecture seule avant toute réception de synchronisation. Il valide les fichiers réels contre le manifeste, relit le paquet et la charge utile, vérifie la destination attendue et authentifie la signature Ed25519 du propriétaire.

## Contrôles
- Vérification complète du manifeste et des octets .papisync / .papidata.
- Relecture et validation structurelle du paquet et de la charge utile.
- Vérification du propriétaire, de la signature, du digest du bundle, des événements, de la destination et de la durée de validité de l'approbation.
- Refus fermé en cas de manifeste, fichier, contenu, identité, signature, destination ou approbation invalide.

## Frontière de sécurité
Le précontrôle appelle la vérification cryptographique avec consume_nonce=False. Il ne crée aucun registre anti-rejeu, ne consomme aucun nonce, n'écrit aucun reçu, n'importe aucun contenu, n'ouvre aucun réseau et n'active aucune exécution. Le nonce peut être consommé entre le précontrôle et la réception : le receiver doit donc refaire les vérifications et effectuer la consommation du nonce avec le reçu dans sa transaction atomique.

## Exemple
```python
from papi_core.sync_transfer_preflight import preflight_sync_transfer

result = preflight_sync_transfer(
    manifest=manifest,
    directory=directory,
    owner_id="owner-id",
    registry_path=registry_path,
    replay_db=replay_db,
    expected_destination="instance-target",
)
assert result["status"] == "preflight_verified"
assert result["receiver_reverification_required"] is True
```

## Vérification
Tests synthétiques : succès sans écriture du registre anti-rejeu, destination erronée, propriétaire inconnu, charge utile altérée et approbation expirée.

## Hors périmètre
Aucun transport réseau, transfert Vercel, connexion Supabase distante, import, worker, scheduler, déploiement ou contact externe.
