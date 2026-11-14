"""Précontrôle local d'un transfert complet, sans effet de bord.""" 
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .sync_bundle_approval import SyncBundleApprovalError, verify_sync_bundle_approval
from .sync_payload import SyncPayloadError, read_sync_payload
from .sync_spool import SyncSpoolError, read_sync_package
from .sync_transfer_manifest import (
    SyncTransferManifestError,
    verify_sync_transfer_manifest_files,
)


class SyncTransferPreflightError(ValueError):
    """Transfert refusé pendant le précontrôle local."""


def preflight_sync_transfer(
    *,
    manifest: object,
    directory: Path,
    owner_id: str,
    registry_path: Path,
    replay_db: Path,
    expected_destination: str,
    now_epoch: int | None = None,
    now: datetime | None = None,
    max_approval_ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Vérifie fichiers, contenu, destination et signature sans consommer le nonce.

    Ce précontrôle ne réserve pas le nonce et ne garantit pas qu'il sera encore
    disponible à la réception. Le receiver doit refaire toutes les vérifications
    et consommer le nonce atomiquement avec son reçu.
    """
    root = Path(directory)
    try:
        verify_sync_transfer_manifest_files(manifest, directory=root)
        if manifest["destination_instance_id"] != expected_destination:
            raise SyncTransferPreflightError("Destination du manifeste inattendue.")
        package_path = root / manifest["package"]["filename"]
        payload_path = root / manifest["payload"]["filename"]
        package = read_sync_package(package_path)
        read_sync_payload(payload_path, bundle=package["bundle"])
        approval = verify_sync_bundle_approval(
            envelope=package["approval"],
            bundle=package["bundle"],
            owner_id=owner_id,
            registry_path=Path(registry_path),
            replay_db=Path(replay_db),
            expected_destination=expected_destination,
            now_epoch=now_epoch,
            now=now,
            max_approval_ttl_seconds=max_approval_ttl_seconds,
            consume_nonce=False,
        )
    except (SyncTransferManifestError, SyncSpoolError, SyncPayloadError,
            SyncBundleApprovalError, KeyError, TypeError) as exc:
        if isinstance(exc, SyncTransferPreflightError):
            raise
        raise SyncTransferPreflightError(str(exc)) from exc

    return {
        "status": "preflight_verified",
        "delivery_id": manifest["delivery_id"],
        "package_digest": package["package_digest"],
        "bundle_digest": package["bundle"]["bundle_digest"],
        "payload_digest": manifest["payload"]["payload_digest"],
        "source_instance_id": package["bundle"]["source_instance_id"],
        "destination_instance_id": expected_destination,
        "owner_id": owner_id,
        "approval_id": approval["approval_id"],
        "signature_verified": True,
        "nonce_consumed": False,
        "receipt_committed": False,
        "import_performed": False,
        "network_transfer_performed": False,
        "execution_enabled": False,
        "receiver_reverification_required": True,
    }
