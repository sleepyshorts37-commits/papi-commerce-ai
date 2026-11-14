# Manifeste de transfert PAPI — Mission 53

## Objectif
La Mission 53 prépare le futur transport inter-instances en produisant un manifeste déterministe qui lie le paquet d'approbation `.papisync` et sa charge utile `.papidata`. Il s'agit d'un contrat local de préparation, pas d'un transport.

## Données liées
Le manifeste référence les noms de fichiers, tailles, SHA-256 des octets, digests internes du paquet et de la charge utile, digest du bundle, source, destination et identifiant d'export. Le `delivery_id` est le SHA-256 canonique de toutes les décisions et métadonnées du manifeste.

## Contrôles
- Fichiers réguliers uniquement ; liens symboliques refusés via `O_NOFOLLOW`.
- Limites individuelles et cumulées de taille.
- JSON UTF-8 canonique, clés dupliquées et constantes non standard refusées.
- Vérification des digests internes et cohérence bundle/charge utile.
- Cohérence de la destination du bundle avec celle de l'approbation.
- Contrat fail-closed : authentification destinataire et approbation propriétaire obligatoires.

## Utilisation locale
```python
from pathlib import Path
from papi_core.sync_transfer_manifest import (
    build_sync_transfer_manifest,
    validate_sync_transfer_manifest,
)

manifest = build_sync_transfer_manifest(
    package_path=Path("./outgoing/package.papisync"),
    payload_path=Path("./outgoing/content.papidata"),
)
assert validate_sync_transfer_manifest(manifest)
```

## Garanties et limites
La fonction ne crée aucun fichier, ne contacte aucun hôte, n'envoie aucune donnée, ne consomme aucun nonce, ne reçoit aucun accusé, n'importe aucun contenu et n'active aucune exécution. Le manifeste n'est pas une signature et ne remplace pas l'approbation Ed25519 : un futur transport devra authentifier le destinataire, vérifier à nouveau la signature et les fichiers, protéger le transfert en transit, appliquer l'anti-rejeu côté réception et demander une validation humaine avant import.

Le format v1 est une première base locale ; toute évolution de schéma devra incrémenter la version et préserver une validation stricte.
