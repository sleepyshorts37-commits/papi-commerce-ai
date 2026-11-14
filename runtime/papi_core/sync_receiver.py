"""Réception locale sécurisée d'un paquet .papisync, sans import de contenu."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .sync_atomic_receipt import AtomicSyncReceiptError, commit_approved_sync_receipt
from .sync_spool import SyncSpoolError, read_sync_package


class SyncReceiverError(ValueError):
    """Paquet refusé par la chaîne de réception locale."""


def receive_sync_package(
    *,
    package_path: Path,
    owner_id: str,
    registry_path: Path,
    ledger_db: Path,
    expected_destination: str,
    now_epoch: int | None = None,
    now: datetime | None = None,
    max_approval_ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Lit, authentifie et inscrit atomiquement un paquet sur l'instance cible.

    Le fichier source est conservé. Seuls le nonce, le reçu et les références
    sont inscrits dans le registre SQLite local; aucun contenu n'est importé.
    """
    try:
        package = read_sync_package(Path(package_path))
        receipt = commit_approved_sync_receipt(
            envelope=package["approval"],
            bundle=package["bundle"],
            owner_id=owner_id,
            registry_path=Path(registry_path),
            ledger_db=Path(ledger_db),
            expected_destination=expected_destination,
            now_epoch=now_epoch,
            now=now,
            max_approval_ttl_seconds=max_approval_ttl_seconds,
        )
    except (SyncSpoolError, AtomicSyncReceiptError) as exc:
        raise SyncReceiverError(str(exc)) from exc

    return {
        "status": receipt["status"],
        "package_digest": package["package_digest"],
        "bundle_digest": receipt["bundle_digest"],
        "approval_id": receipt["latest_verified_approval_id"],
        "destination_instance_id": expected_destination,
        "event_count": receipt["event_count"],
        "signature_verified": True,
        "nonce_consumed_atomically": receipt["nonce_consumed_atomically"],
        "receipt_committed": receipt["receipt_committed"],
        "package_retained": True,
        "import_performed": False,
        "execution_enabled": False,
        "ledger_scope": receipt["ledger_scope"],
    }
