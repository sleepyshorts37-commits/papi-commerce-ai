# Manifeste de transfert PAPI — Vérification locale

## Vérification après préparation ou copie manuelle
Le manifeste de Mission 53 décrit les deux fichiers attendus. La fonction `verify_sync_transfer_manifest_files` relit les fichiers réellement présents dans un dossier local, reconstruit le manifeste et compare sa représentation canonique au manifeste initial.

```python
from pathlib import Path
from papi_core.sync_transfer_manifest import (
    build_sync_transfer_manifest,
    verify_sync_transfer_manifest_files,
)

directory = Path("./outgoing")
manifest = build_sync_transfer_manifest(
    package_path=directory / "package.papisync",
    payload_path=directory / "content.papidata",
)
assert verify_sync_transfer_manifest_files(manifest, directory=directory)
```

## Refus systématiques
- Manifeste altéré ou champs de mauvais type.
- Fichier absent, lien symbolique, fichier non régulier ou octets modifiés.
- Répertoire de transfert symbolique ou inexistant.
- Nom de fichier ne correspondant pas exactement au digest attendu.
- Taille supérieure aux limites du protocole.

La vérification est en lecture seule. Elle ne signe pas le manifeste, n'authentifie pas un expéditeur distant, ne consomme aucun nonce et ne prouve pas qu'une approbation Ed25519 est valide. La réception doit toujours refaire ses contrôles cryptographiques et d'anti-rejeu avant toute opération.
