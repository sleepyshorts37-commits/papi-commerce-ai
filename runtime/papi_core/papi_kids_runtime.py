"""Construct the real PKP-0001 runtime from server-only environment secrets.

Construction performs no network request. The provider is contacted only after
the caller separately authorizes execution through the book orchestrator.
"""
from __future__ import annotations

import os
from typing import Any, Callable

from .image_asset_center import LocalImageAssetCenter
from .image_model_router import FreeImageModel, FreeImageModelRouter
from .image_production_engine import ImageProductionEngine
from .image_provider_cloudflare import CloudflareImageAdapter
from .image_provider_registry import ProviderRegistryError
from .papi_kids_orchestrator import PapiKidsOrchestrationError


class PapiKidsRuntimeError(ValueError):
    """Missing runtime configuration or unsafe provider selection."""


REQUIRED_SERVER_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
)


def build_pkp0001_runtime_engine(
    *,
    registry: Any,
    account_refs: dict[str, str],
    quota_evidence_by_model: dict[str, dict[str, Any]],
    asset_center: LocalImageAssetCenter,
    operator_confirmed_free_tier: bool,
    transport: Callable[..., Any] | None = None,
    max_batch_size: int = 4,
) -> tuple[ImageProductionEngine, dict[str, Any]]:
    """Build an engine with Cloudflare and the shared Supabase quota ledger."""
    if operator_confirmed_free_tier is not True:
        raise PapiKidsRuntimeError("Confirmation opérateur du forfait gratuit absente.")
    missing = [key for key in REQUIRED_SERVER_ENV if not os.getenv(key)]
    if missing:
        raise PapiKidsRuntimeError(
            "Configuration serveur incomplète : " + ", ".join(missing)
        )
    try:
        selected = registry.choose(
            account_refs=account_refs,
            quota_evidence_by_model=quota_evidence_by_model,
            required_images=24,
            spend_cap_minor=0,
        )
    except (ProviderRegistryError, AttributeError, TypeError) as exc:
        raise PapiKidsRuntimeError("Aucun modèle image admissible dans le registre.") from exc
    if selected.get("provider_id") != "cloudflare":
        raise PapiKidsRuntimeError("Seul l'adaptateur Cloudflare est intégré à PKP-0001.")
    model_id = selected["model_id"]
    cost = selected["estimated_units_per_image"]
    try:
        provider = CloudflareImageAdapter.from_shared_environment(
            model_costs={model_id: cost},
            free_tier_confirmed_for_account=True,
            transport=transport,
        )
        router = FreeImageModelRouter(
            provider=provider,
            models=[FreeImageModel(model_id, cost, True)],
            max_batch_size=max_batch_size,
        )
        engine = ImageProductionEngine(
            generator=router,
            asset_center=asset_center,
            max_batch_size=max_batch_size,
        )
    except Exception as exc:
        # Never expose secret values in exception text or logs.
        raise PapiKidsRuntimeError(
            f"Impossible de construire le runtime image ({type(exc).__name__})."
        ) from exc
    return engine, {
        "provider_id": "cloudflare",
        "model_id": model_id,
        "estimated_units_per_image": cost,
        "quota_ledger": "supabase_transactional_shared",
        "server_secrets_loaded": True,
        "network_called": False,
        "paid_fallback": False,
        "spend_cap_minor": 0,
    }
