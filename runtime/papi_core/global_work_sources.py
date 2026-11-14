"""Contrat local d'ingestion des sources PAPI GLOBAL WORK.

Ce module ne réalise aucune requête réseau. Il valide un registre de sources
et normalise des enregistrements déjà obtenus par un canal autorisé.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .global_work import validate_opportunity

ALLOWED_KINDS = {"official_api", "rss", "manual_import"}
ALLOWED_POLICIES = {"allowed", "owner_review", "prohibited"}
SOURCE_REGISTRY_FILE = Path(__file__).resolve().parents[2] / "data" / "global-work-sources.json"
SOURCE_FIELDS = {
    "id", "name", "kind", "access_policy", "enabled", "terms_url",
    "allowed_countries", "notes",
}


class GlobalWorkSourceError(ValueError):
    """Registre de sources ou lot d'ingestion invalide."""


def _https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    from urllib.parse import urlparse
    parsed = urlparse(value)
    return bool(parsed.hostname) and not parsed.username and not parsed.password


def validate_source_registry(data: dict[str, Any]) -> list[str]:
    if not isinstance(data, dict) or data.get("project") != "PAPI COMMERCE AI":
        return ["Registre des sources GLOBAL WORK invalide."]
    if data.get("schema_version") != "1.0":
        return ["Version du registre des sources non prise en charge."]
    if set(data) - {"project", "schema_version", "sources", "note"}:
        return ["Sections inconnues dans le registre des sources."]
    sources = data.get("sources")
    if not isinstance(sources, list):
        return ["sources doit être une liste."]
    errors: list[str] = []
    seen: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix}: objet attendu.")
            continue
        missing = SOURCE_FIELDS - set(source)
        extra = set(source) - SOURCE_FIELDS
        if missing:
            errors.append(f"{prefix}: champs absents: {', '.join(sorted(missing))}.")
        if extra:
            errors.append(f"{prefix}: champs inconnus: {', '.join(sorted(extra))}.")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{prefix}: id non vide requis.")
        elif source_id in seen:
            errors.append(f"{prefix}: identifiant dupliqué {source_id}.")
        else:
            seen.add(source_id)
        if not isinstance(source.get("name"), str) or not source.get("name", "").strip():
            errors.append(f"{prefix}: name non vide requis.")
        if source.get("kind") not in ALLOWED_KINDS:
            errors.append(f"{prefix}: kind invalide.")
        if source.get("access_policy") not in ALLOWED_POLICIES:
            errors.append(f"{prefix}: access_policy invalide.")
        if not isinstance(source.get("enabled"), bool):
            errors.append(f"{prefix}: enabled doit être booléen.")
        if not _https_url(source.get("terms_url")):
            errors.append(f"{prefix}: terms_url doit être une URL HTTPS publique.")
        countries = source.get("allowed_countries")
        if not isinstance(countries, list) or any(not isinstance(c, str) or not c.strip() for c in countries):
            errors.append(f"{prefix}: allowed_countries doit être une liste de pays.")
        if not isinstance(source.get("notes"), str):
            errors.append(f"{prefix}: notes doit être un texte.")
    return errors


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def ingest_records(
    source_registry: dict[str, Any],
    *,
    source_id: str,
    fetched_at: str,
    records: list[dict[str, Any]],
    existing_opportunity_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Valide un lot déjà collecté et renvoie les entrées acceptées/rejetées.

    Les sources désactivées, interdites ou soumises à revue du propriétaire
    sont bloquées. Aucun téléchargement ni contact externe n'est déclenché.
    """
    registry_errors = validate_source_registry(source_registry)
    if registry_errors:
        raise GlobalWorkSourceError("; ".join(registry_errors))
    if not _valid_timestamp(fetched_at):
        raise GlobalWorkSourceError("fetched_at doit être un horodatage ISO-8601 avec fuseau.")
    source = next((item for item in source_registry["sources"] if item["id"] == source_id), None)
    if source is None:
        raise GlobalWorkSourceError("Source inconnue.")
    if not source["enabled"] or source["access_policy"] != "allowed":
        raise GlobalWorkSourceError("Source désactivée ou non autorisée pour l'ingestion.")
    if not isinstance(records, list):
        raise GlobalWorkSourceError("records doit être une liste.")

    seen = set(existing_opportunity_ids)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for index, record in enumerate(records):
        errors = validate_opportunity(record) if isinstance(record, dict) else ["Objet attendu."]
        record_id = record.get("id") if isinstance(record, dict) else None
        if isinstance(record_id, str) and record_id in seen:
            errors.append("Identifiant déjà présent : doublon ignoré.")
        if errors:
            rejected.append({"index": str(index), "record_id": str(record_id or ""), "reason": " ".join(errors)})
            continue
        seen.add(record_id)
        accepted.append({
            "opportunity": dict(record),
            "provenance": {
                "source_id": source_id,
                "source_name": source["name"],
                "source_kind": source["kind"],
                "terms_url": source["terms_url"],
                "fetched_at": fetched_at,
                "ingestion_mode": "pre_fetched_authorized_payload",
            },
        })
    return {
        "source_id": source_id,
        "accepted": accepted,
        "rejected": rejected,
        "external_fetch_performed": False,
        "application_submitted": False,
    }


def load_source_registry(path: Path = SOURCE_REGISTRY_FILE) -> dict[str, Any]:
    """Charge et valide le registre local des sources."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GlobalWorkSourceError("Impossible de lire le registre des sources GLOBAL WORK.") from exc
    errors = validate_source_registry(data)
    if errors:
        raise GlobalWorkSourceError("; ".join(errors))
    return data
