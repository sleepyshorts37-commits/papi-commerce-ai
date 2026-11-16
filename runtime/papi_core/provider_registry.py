"""PAPI CONNECT provider registry: local validation and authorization only."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "data" / "providers.json"
STATUSES = {"proposed", "verified", "enabled", "disabled", "deprecated"}
PRICING_MODELS = {"unknown", "free", "quota", "trial", "usage_based", "subscription", "one_time"}
CATEGORIES = {"llm", "automation", "observability", "storage", "tools", "local_runtime", "search", "media", "other"}
DATA_CLASSES = {"public", "internal", "confidential", "personal", "financial", "credentials"}
PROVIDER_ID = re.compile(r"^[a-z][a-z0-9._-]{2,63}$")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")

class ProviderRegistryError(ValueError):
    """Invalid registry data or forbidden provider access."""

def validate_provider(provider: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(provider, dict):
        return ["Each provider must be an object."]
    required = {"id", "name", "category", "capabilities", "status", "enabled", "external", "pricing", "quota", "required_permissions", "credentials_env", "data_classes", "region_scope", "docs_url", "pricing_url", "last_verified_at", "owner_approval_required"}
    missing = required - provider.keys()
    if missing:
        return ["Missing required fields: " + ", ".join(sorted(missing))]
    if not isinstance(provider["id"], str) or not PROVIDER_ID.fullmatch(provider["id"]):
        errors.append("Invalid provider id.")
    if not isinstance(provider["name"], str) or not provider["name"].strip():
        errors.append("Provider name is required.")
    if not isinstance(provider["category"], str) or provider["category"] not in CATEGORIES:
        errors.append("Invalid provider category.")
    if not isinstance(provider["status"], str) or provider["status"] not in STATUSES:
        errors.append("Invalid provider status.")
    for field in ("enabled", "external", "owner_approval_required"):
        if not isinstance(provider[field], bool):
            errors.append(field + " must be boolean.")
    if provider["enabled"] and provider["status"] != "enabled":
        errors.append("An enabled provider must have status enabled.")
    if provider["status"] == "enabled" and not provider["enabled"]:
        errors.append("Status enabled requires enabled=true.")
    for field in ("capabilities", "required_permissions", "credentials_env", "data_classes"):
        value = provider[field]
        if not isinstance(value, list) or (field in {"capabilities", "data_classes"} and not value):
            errors.append(field + " must be a valid list.")
        elif any(not isinstance(item, str) for item in value):
            errors.append(field + " must contain strings only.")
        elif len(value) != len(set(value)):
            errors.append(field + " must not contain duplicates.")
    if isinstance(provider["credentials_env"], list) and any(not isinstance(v, str) or not ENV_NAME.fullmatch(v) for v in provider["credentials_env"]):
        errors.append("credentials_env must contain environment variable names only.")
    if isinstance(provider["data_classes"], list) and any(v not in DATA_CLASSES for v in provider["data_classes"]):
        errors.append("Unknown data classification.")
    pricing = provider["pricing"]
    if not isinstance(pricing, dict) or not {"model", "currency", "free_quota", "trial_days", "notes"} <= pricing.keys():
        errors.append("Incomplete pricing object.")
    elif not isinstance(pricing["model"], str) or pricing["model"] not in PRICING_MODELS:
        errors.append("Invalid pricing model.")
    quota = provider["quota"]
    if not isinstance(quota, dict) or not {"requests_per_minute", "requests_per_day", "monthly_limit", "max_cost_xof"} <= quota.keys():
        errors.append("Incomplete quota object.")
    elif not isinstance(quota["max_cost_xof"], int) or isinstance(quota["max_cost_xof"], bool) or quota["max_cost_xof"] < 0:
        errors.append("max_cost_xof must be a non-negative integer.")
    for field in ("docs_url", "pricing_url"):
        if not isinstance(provider[field], str) or not provider[field].startswith("https://"):
            errors.append(field + " must be an HTTPS URL.")
    verified = provider["last_verified_at"]
    if verified is not None and (not isinstance(verified, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", verified)):
        errors.append("last_verified_at must be an ISO date or null.")
    if provider["status"] in {"verified", "enabled"} and verified is None:
        errors.append("Verified or enabled providers require a verification date.")
    if provider["external"] and provider["status"] == "enabled" and not provider["owner_approval_required"]:
        errors.append("External providers require owner approval.")
    return errors

def validate_catalog(catalog: Any) -> list[str]:
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.0.0":
        return ["Missing or unsupported registry schema version."]
    providers = catalog.get("providers")
    if not isinstance(providers, list):
        return ["providers must be a list."]
    errors: list[str] = []
    seen: set[str] = set()
    for index, provider in enumerate(providers):
        errors.extend(f"Provider #{index + 1}: {error}" for error in validate_provider(provider))
        if isinstance(provider, dict) and isinstance(provider.get("id"), str):
            if provider["id"] in seen:
                errors.append("Duplicate provider id: " + provider["id"])
            seen.add(provider["id"])
    return errors

def load_provider_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderRegistryError(f"Cannot read provider registry: {exc}") from exc
    errors = validate_catalog(catalog)
    if errors:
        raise ProviderRegistryError("; ".join(errors))
    return catalog

def find_providers(capability: str | None = None, status: str | None = None, path: Path = DEFAULT_CATALOG) -> list[dict[str, Any]]:
    """Read-only catalogue search; does not connect or enable providers."""
    return [p for p in load_provider_catalog(path)["providers"] if (capability is None or capability in p["capabilities"]) and (status is None or status == p["status"])]

def authorize_provider(provider: dict[str, Any], agent_permissions: set[str], owner_approved: bool = False) -> None:
    """Fail-closed permission check; returns no secrets and makes no network call."""
    errors = validate_provider(provider)
    if errors:
        raise ProviderRegistryError("; ".join(errors))
    if provider["status"] != "enabled" or not provider["enabled"]:
        raise ProviderRegistryError("Provider is disabled or not verified yet.")
    if not set(provider["required_permissions"]).issubset(agent_permissions):
        raise ProviderRegistryError("Agent permissions are insufficient.")
    if provider["external"] and provider["owner_approval_required"] and not owner_approved:
        raise ProviderRegistryError("Explicit owner approval is required for this external provider.")
