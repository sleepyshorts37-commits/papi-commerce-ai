"""One-shot opt-in offsite transfer of encrypted backups."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .papi_kids_offsite_backup import (
    PapiKidsOffsiteBackupError,
    copy_encrypted_backups_offsite,
)


def main() -> int:
    if os.environ.get("PAPI_KIDS_OFFSITE_ENABLED", "false").lower() != "true":
        raise PapiKidsOffsiteBackupError("Transfert hors site désactivé.")
    directory = os.environ.get("PAPI_KIDS_BACKUP_DIRECTORY", "")
    remote = os.environ.get("PAPI_KIDS_BACKUP_REMOTE", "")
    result = copy_encrypted_backups_offsite(
        directory, remote=remote,
        enabled=True,
    )
    print(json.dumps({
        "status": result["status"],
        "remote": result["remote"],
        "files_copied_and_checked": result["files_copied_and_checked"],
        "remote_deletions_performed": False,
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
