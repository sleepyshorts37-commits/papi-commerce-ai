#!/usr/bin/env python3
"""Validate the versioned Supabase migration inventory without connecting to a database."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "infra" / "supabase" / "migrations"
MANIFEST = MIGRATIONS_DIR / "manifest.json"
VERSION_RE = re.compile(r"^(\d{8}_\d{3})_([a-z0-9_]+)_(up|down)\.sql$")


def validate() -> list[str]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported migration manifest schema_version")
    policy = data.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    if policy.get("execution_enabled") is not False:
        raise ValueError("migration execution must remain disabled")
    if policy.get("production_execution_allowed") is not False:
        raise ValueError("production migration execution must remain disabled")
    if policy.get("require_human_approval") is not True:
        raise ValueError("human approval must be required")

    entries = data.get("migrations")
    if not isinstance(entries, list):
        raise ValueError("migrations must be a list")

    versions: list[str] = []
    registered_files: set[str] = set()
    output: list[str] = []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("each migration entry must be an object")
        version = item.get("version")
        name = item.get("name")
        if not isinstance(version, str) or not re.fullmatch(r"\d{8}_\d{3}", version):
            raise ValueError(f"invalid migration version: {version!r}")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError(f"invalid migration name for {version}")
        if item.get("status") != "repository_only_not_applied":
            raise ValueError(f"{version}: manifest must not claim a migration was applied")
        if item.get("rollback_policy") in (None, ""):
            raise ValueError(f"{version}: rollback policy is required")

        expected = {
            "up": f"{version}_{name}_up.sql",
            "down": f"{version}_{name}_down.sql",
        }
        for direction, filename in expected.items():
            if item.get(direction) != filename:
                raise ValueError(f"{version}: {direction} filename must be {filename}")
            path = MIGRATIONS_DIR / filename
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise ValueError(f"missing or empty migration file: {filename}")
            registered_files.add(filename)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            output.append(f"{version} {direction.upper()} sha256={digest} file={filename}")

        versions.append(version)

    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise ValueError("migration versions must be unique and ascending")

    discovered = {
        path.name for path in MIGRATIONS_DIR.glob("*.sql")
        if VERSION_RE.fullmatch(path.name)
    }
    if discovered != registered_files:
        missing = sorted(discovered - registered_files)
        stale = sorted(registered_files - discovered)
        raise ValueError(f"manifest/file inventory mismatch; unregistered={missing}, missing={stale}")

    return output


if __name__ == "__main__":
    try:
        for line in validate():
            print(line)
        print("Migration manifest valid. No database connection or migration execution performed.")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Migration manifest invalid: {exc}", file=sys.stderr)
        raise SystemExit(1)
