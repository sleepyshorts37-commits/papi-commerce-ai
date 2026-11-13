"""Freshness, duplicate detection and conservative quality checks for job leads."""
from __future__ import annotations

import hashlib
import ipaddress
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
TRACKING_PREFIXES = ("utm_",)
MAX_TITLE_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 4000


class GlobalWorkQualityError(ValueError):
    """Invalid discovery candidate or evaluation input."""


def _utc(value: str | datetime) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GlobalWorkQualityError("Date ISO-8601 invalide.") from exc
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise GlobalWorkQualityError("Une date avec fuseau horaire est requise.")
    return value.astimezone(timezone.utc)


def canonicalize_url(url: str) -> str:
    """Normalize a public HTTPS URL for duplicate detection without following redirects."""
    if not isinstance(url, str):
        raise GlobalWorkQualityError("URL texte requise.")
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise GlobalWorkQualityError("URL ou port invalide.") from exc
    if (parts.scheme.lower() != "https" or not host or parts.username or parts.password
            or port not in (None, 443)):
        raise GlobalWorkQualityError("URL HTTPS publique requise.")
    host = host.lower().rstrip(".")
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise GlobalWorkQualityError("Hôte local ou privé interdit.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise GlobalWorkQualityError("Adresse IP non publique interdite.")
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS
        and not any(key.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)
    ]
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))


def fingerprint_candidate(candidate: dict[str, Any]) -> str:
    """Stable fingerprint based on canonical URL; fallback to normalized title."""
    if not isinstance(candidate, dict):
        raise GlobalWorkQualityError("Candidat invalide.")
    url = candidate.get("source_url") or candidate.get("url")
    if url:
        identity = canonicalize_url(url)
    else:
        title = candidate.get("title")
        if not isinstance(title, str) or not title.strip():
            raise GlobalWorkQualityError("URL ou titre requis pour dédoublonner.")
        identity = "title:" + " ".join(title.casefold().split())
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def evaluate_candidate_freshness(
    candidate: dict[str, Any], *, now: str | datetime, max_age_days: int = 30
) -> dict[str, Any]:
    """Return freshness state; missing/invalid publication date is never assumed fresh."""
    if not isinstance(candidate, dict):
        raise GlobalWorkQualityError("Candidat invalide.")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or max_age_days < 0:
        raise GlobalWorkQualityError("max_age_days doit être un entier positif ou nul.")
    current = _utc(now)
    published = candidate.get("published_at")
    if not published:
        return {"freshness": "unknown", "age_days": None, "eligible_for_auto_queue": False}
    date = _utc(published)
    age = (current - date).total_seconds() / 86400
    if age < 0:
        return {"freshness": "future_date", "age_days": round(age, 2), "eligible_for_auto_queue": False}
    if age > max_age_days:
        return {"freshness": "stale", "age_days": round(age, 2), "eligible_for_auto_queue": False}
    return {"freshness": "fresh", "age_days": round(age, 2), "eligible_for_auto_queue": True}


def assess_candidate_quality(candidate: dict[str, Any]) -> dict[str, Any]:
    """Check completeness without fabricating missing values or approving the offer."""
    if not isinstance(candidate, dict):
        raise GlobalWorkQualityError("Candidat invalide.")
    required = ("title", "source_id", "source_url")
    missing = [field for field in required if not isinstance(candidate.get(field), str)
               or not candidate[field].strip()]
    title = candidate.get("title", "")
    description = candidate.get("description", "")
    if isinstance(title, str) and len(title) > MAX_TITLE_LENGTH:
        missing.append("title_length_invalid")
    if isinstance(description, str) and len(description) > MAX_DESCRIPTION_LENGTH:
        missing.append("description_length_invalid")
    try:
        canonicalize_url(candidate.get("source_url", ""))
    except GlobalWorkQualityError:
        missing.append("source_url_invalid")
    declared_missing = candidate.get("missing_fields", [])
    if isinstance(declared_missing, list):
        missing.extend(str(item) for item in declared_missing)
    unique_missing = sorted(set(missing))
    return {
        "quality": "incomplete" if unique_missing else "needs_human_review",
        "missing_fields": unique_missing,
        "qualified": False,
        "application_submitted": False,
    }


def deduplicate_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep first occurrence and report duplicates; preserve original candidate objects."""
    if not isinstance(candidates, list):
        raise GlobalWorkQualityError("Une liste de candidats est requise.")
    seen: dict[str, int] = {}
    unique, duplicates = [], []
    for index, candidate in enumerate(candidates):
        fingerprint = fingerprint_candidate(candidate)
        if fingerprint in seen:
            duplicates.append({"index": index, "duplicate_of": seen[fingerprint],
                               "fingerprint": fingerprint})
        else:
            seen[fingerprint] = index
            unique.append(candidate)
    return {"unique_candidates": unique, "duplicates": duplicates,
            "input_count": len(candidates), "unique_count": len(unique),
            "duplicate_count": len(duplicates)}
