"""Read-only parsers for authorized PAPI GLOBAL WORK feed payloads.

No network requests are made here. Payloads must be supplied by an external,
approved fetch mechanism; this module only parses and normalizes them.
"""
from __future__ import annotations

import ipaddress
import json
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

MAX_PAYLOAD_BYTES = 1_000_000
MAX_ITEMS = 100


class GlobalWorkAdapterError(ValueError):
    """Invalid or unsupported feed payload."""


def _validate_public_https_url(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise GlobalWorkAdapterError(f"{field}: URL texte requise.")
    try:
        parsed = urlparse(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise GlobalWorkAdapterError(f"{field}: URL ou port invalide.") from exc
    if (parsed.scheme.lower() != "https" or not host or parsed.username
            or parsed.password or port not in (None, 443)):
        raise GlobalWorkAdapterError(f"{field}: URL HTTPS publique requise.")
    if any(ord(char) < 32 for char in value):
        raise GlobalWorkAdapterError(f"{field}: caractères de contrôle interdits.")
    host = host.lower().rstrip(".")
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise GlobalWorkAdapterError(f"{field}: hôte local ou privé interdit.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise GlobalWorkAdapterError(f"{field}: adresse IP non publique interdite.")
    return value


def _payload_text(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise GlobalWorkAdapterError("Payload trop volumineux.")
        try:
            payload = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise GlobalWorkAdapterError("Le payload doit être encodé en UTF-8.") from exc
    elif not isinstance(payload, str):
        raise GlobalWorkAdapterError("Payload texte ou bytes attendu.")
    if len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise GlobalWorkAdapterError("Payload trop volumineux.")
    return payload


def parse_rss_payload(payload: str | bytes, *, source_id: str) -> list[dict[str, Any]]:
    """Parse RSS 2.0 items into unqualified discovery candidates."""
    text = _payload_text(payload)
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, flags=re.IGNORECASE):
        raise GlobalWorkAdapterError("DTD et entités XML externes sont interdits.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise GlobalWorkAdapterError("Flux RSS XML invalide.") from exc
    if root.tag.split("}")[-1].casefold() != "rss":
        raise GlobalWorkAdapterError("Le document doit être un flux RSS.")
    channel = next((node for node in root if node.tag.split("}")[-1].casefold() == "channel"), None)
    if channel is None:
        raise GlobalWorkAdapterError("Canal RSS absent.")
    items = [node for node in channel if node.tag.split("}")[-1].casefold() == "item"]
    if len(items) > MAX_ITEMS:
        raise GlobalWorkAdapterError("Trop d'éléments dans le flux.")
    candidates = []
    for index, item in enumerate(items):
        fields = {child.tag.split("}")[-1].casefold(): (child.text or "").strip()
                  for child in item}
        if not fields.get("title") or not fields.get("link"):
            continue
        link = _validate_public_https_url(fields["link"], "link")
        candidates.append({
            "candidate_id": f"{source_id}:{index}",
            "source_id": source_id,
            "title": fields["title"][:300],
            "description": fields.get("description", "")[:4000],
            "source_url": link,
            "published_at": fields.get("pubdate") or fields.get("published") or None,
            "qualification_status": "unverified",
            "missing_fields": [
                "country_eligibility", "eligible_countries", "compensation_amount",
                "currency", "estimated_minutes", "upfront_cost", "automation_policy",
                "ai_policy", "human_presence_required", "payout_methods",
            ],
            "application_submitted": False,
        })
    return candidates


def parse_json_api_payload(payload: str | bytes, *, source_id: str) -> list[dict[str, Any]]:
    """Parse a documented JSON feed using a conservative item contract.

    Expected root: an array, or an object with an `items` array. Each item
    requires title and url; description and published_at are optional.
    """
    text = _payload_text(payload)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GlobalWorkAdapterError("Payload JSON invalide.") from exc
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise GlobalWorkAdapterError("Le payload doit contenir au maximum 100 éléments.")
    candidates = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title, url = item.get("title"), item.get("url")
        if not isinstance(title, str) or not title.strip():
            continue
        url = _validate_public_https_url(url, "url")
        description = item.get("description", "")
        if not isinstance(description, str):
            description = ""
        published_at = item.get("published_at")
        if published_at is not None and not isinstance(published_at, str):
            published_at = None
        candidates.append({
            "candidate_id": f"{source_id}:{index}",
            "source_id": source_id,
            "title": title.strip()[:300],
            "description": description.strip()[:4000],
            "source_url": url,
            "published_at": published_at,
            "qualification_status": "unverified",
            "missing_fields": [
                "country_eligibility", "eligible_countries", "compensation_amount",
                "currency", "estimated_minutes", "upfront_cost", "automation_policy",
                "ai_policy", "human_presence_required", "payout_methods",
            ],
            "application_submitted": False,
        })
    return candidates
