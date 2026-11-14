"""Validation locale de paquets de synchronisation référentiels (sans transport)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

PROTOCOL_VERSION = "1.0"
MAX_EVENTS = 500
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_KINDS = {"memory", "message"}


class SyncBundleError(ValueError):
    """Paquet de synchronisation invalide ou non sûr."""


def _canonical_digest(value: dict) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SyncBundleError("Le paquet contient une valeur non canonique.") from exc
    return hashlib.sha256(raw).hexdigest()


def _timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validate_event(event: object, previous_sequence: int) -> int:
    required = {"event_id", "kind", "record_id", "sequence", "content_digest"}
    if not isinstance(event, dict) or set(event) != required:
        raise SyncBundleError("Structure d'événement invalide.")
    if (not isinstance(event["event_id"], str) or not _ID.fullmatch(event["event_id"])
            or not isinstance(event["record_id"], str) or not _ID.fullmatch(event["record_id"])
            or event["kind"] not in _KINDS
            or not isinstance(event["content_digest"], str)
            or not _SHA256.fullmatch(event["content_digest"])):
        raise SyncBundleError("Référence ou empreinte d'événement invalide.")
    sequence = event["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= previous_sequence:
        raise SyncBundleError("Séquence invalide, répétée ou non croissante.")
    return sequence


def build_sync_bundle(*, source_instance_id: str, destination_instance_id: str,
                      export_id: str, created_at: str, cursor_start: int,
                      cursor_end: int, events: list[dict]) -> dict:
    """Construit un paquet référentiel canonique; aucun contenu métier n'est inclus."""
    if (not all(isinstance(v, str) and _ID.fullmatch(v) for v in
                (source_instance_id, destination_instance_id, export_id))
            or source_instance_id == destination_instance_id):
        raise SyncBundleError("Identités d'instances ou export_id invalides.")
    if not _timestamp(created_at):
        raise SyncBundleError("created_at doit être ISO-8601 avec fuseau.")
    if (isinstance(cursor_start, bool) or not isinstance(cursor_start, int)
            or isinstance(cursor_end, bool) or not isinstance(cursor_end, int)
            or cursor_start < 0 or cursor_end < cursor_start - 1):
        raise SyncBundleError("Bornes de curseur invalides.")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise SyncBundleError("Liste d'événements invalide ou hors limites.")
    normalized = []
    seen_events, seen_records = set(), set()
    previous = cursor_start - 1
    for event in events:
        previous = _validate_event(event, previous)
        if previous != (cursor_start - 1 if not normalized else normalized[-1]["sequence"]) + 1 or not cursor_start <= previous <= cursor_end:
            raise SyncBundleError("Séquence hors de la plage du paquet.")
        if event["event_id"] in seen_events:
            raise SyncBundleError("Identifiant d'événement dupliqué.")
        key = (event["kind"], event["record_id"])
        if key in seen_records:
            raise SyncBundleError("Ressource répétée dans le paquet.")
        seen_events.add(event["event_id"])
        seen_records.add(key)
        normalized.append(dict(event))
    if normalized and (normalized[0]["sequence"] != cursor_start
                       or normalized[-1]["sequence"] != cursor_end):
        raise SyncBundleError("Les événements ne couvrent pas exactement les curseurs déclarés.")
    if not normalized and cursor_start != cursor_end + 1:
        raise SyncBundleError("Un paquet vide doit utiliser une plage vide (cursor_start > cursor_end).")
    bundle = {
        "protocol_version": PROTOCOL_VERSION,
        "source_instance_id": source_instance_id,
        "destination_instance_id": destination_instance_id,
        "export_id": export_id,
        "created_at": created_at,
        "cursor_start": cursor_start,
        "cursor_end": cursor_end,
        "events": normalized,
    }
    bundle["bundle_digest"] = _canonical_digest(bundle)
    return bundle


def validate_sync_bundle(bundle: object, *, expected_destination: str | None = None) -> bool:
    """Valide intégrité et forme; ne prouve ni signature ni approbation."""
    if not isinstance(bundle, dict) or set(bundle) != {
        "protocol_version", "source_instance_id", "destination_instance_id",
        "export_id", "created_at", "cursor_start", "cursor_end", "events", "bundle_digest"
    }:
        raise SyncBundleError("Enveloppe du paquet invalide.")
    if bundle["protocol_version"] != PROTOCOL_VERSION:
        raise SyncBundleError("Version de protocole non prise en charge.")
    if expected_destination is not None and bundle["destination_instance_id"] != expected_destination:
        raise SyncBundleError("Destination du paquet inattendue.")
    digest = bundle["bundle_digest"]
    unsigned = {key: value for key, value in bundle.items() if key != "bundle_digest"}
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest) or _canonical_digest(unsigned) != digest:
        raise SyncBundleError("Empreinte du paquet absente ou altérée.")
    rebuilt = build_sync_bundle(
        source_instance_id=bundle["source_instance_id"],
        destination_instance_id=bundle["destination_instance_id"],
        export_id=bundle["export_id"], created_at=bundle["created_at"],
        cursor_start=bundle["cursor_start"], cursor_end=bundle["cursor_end"],
        events=bundle["events"],
    )
    if rebuilt["bundle_digest"] != digest:
        raise SyncBundleError("Le paquet ne respecte pas le contrat canonique.")
    return True
