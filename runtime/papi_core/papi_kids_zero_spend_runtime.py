"""PKP-0001 runtime builder wiring the zero-spend FLUX gate to the image engine."""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
from typing import Any, Callable

from .image_model_router import FreeImageModel, FreeImageModelRouter
from .image_production_engine import ImageProductionEngine
from .papi_kids_asset_center_adapter import PapiKidsIllustrationAssetCenter
from .papi_kids_image_batch_adapter import CloudflareFluxSchnellBatchAdapter
from .papi_kids_image_provider import (
    MODEL_ID, SOURCE_PRICING, CloudflareFluxSchnellProvider,
    ImageProviderBlocked, PostgresNeuronReservationStore,
    estimate_flux_schnell_neurons, validate_free_quota_evidence,
)
from .papi_kids_postgres_queue import build_postgres_asset_registrar
from .papi_kids_worker_service import create_postgres_connection_factory


class PapiKidsZeroSpendRuntimeError(ValueError):
    """The free-tier image runtime is not safe or eligible to construct."""


def build_pkp0001_zero_spend_runtime_engine(
    *,
    upload_id: str,
    storage_root: str | Path,
    registry: Any,
    account_refs: dict[str, str],
    quota_evidence_by_model: dict[str, dict[str, Any]],
    operator_confirmed_free_tier: bool,
    generation_authorized: bool = False,
    account_id: str | None = None,
    api_token: str | None = None,
    connection_factory: Callable[[], Any] | None = None,
    reservation_store: Any | None = None,
    asset_registrar: Callable[[dict[str, Any]], Any] | None = None,
    transport: Callable[..., Any] | None = None,
    max_batch_size: int = 4,
) -> tuple[ImageProductionEngine, dict[str, Any]]:
    """Construct only; no HTTP request or image generation occurs in this function."""
    if not isinstance(upload_id, str) or not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
        raise PapiKidsZeroSpendRuntimeError("Référence de manuscrit invalide.")
    root = Path(storage_root).resolve()
    if not root.is_dir() or not (root / upload_id).is_dir():
        raise PapiKidsZeroSpendRuntimeError("Volume privé ou dossier de manuscrit absent.")
    if operator_confirmed_free_tier is not True:
        raise PapiKidsZeroSpendRuntimeError("Confirmation du forfait Workers Free obligatoire.")
    if not isinstance(generation_authorized, bool):
        raise PapiKidsZeroSpendRuntimeError("Autorisation de génération invalide.")
    if not isinstance(max_batch_size, int) or isinstance(max_batch_size, bool) or not 1 <= max_batch_size <= 4:
        raise PapiKidsZeroSpendRuntimeError("Les lots image sont limités à quatre pages.")
    account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not isinstance(account_id, str) or not re.fullmatch(r"[a-f0-9]{32}", account_id) or not api_token:
        raise PapiKidsZeroSpendRuntimeError("Identifiants Cloudflare serveur absents ou invalides.")
    if not isinstance(account_refs, dict) or account_refs.get("cloudflare") != account_id:
        raise PapiKidsZeroSpendRuntimeError("Référence du compte différente du secret serveur.")

    evidence = quota_evidence_by_model.get(MODEL_ID) if isinstance(quota_evidence_by_model, dict) else None
    campaign_neurons = estimate_flux_schnell_neurons(1024, 1024, 4) * 24
    try:
        validate_free_quota_evidence(evidence, required_neurons=campaign_neurons)
    except ImageProviderBlocked as exc:
        raise PapiKidsZeroSpendRuntimeError(str(exc)) from exc

    registry_evidence = {
        "provider": "cloudflare",
        "account_ref": account_id,
        "model_id": MODEL_ID,
        "source_url": SOURCE_PRICING,
        "evidence_ref": evidence["evidence_ref"],
        "verified_at": evidence["quota_checked_at"],
        "expires_at": evidence["evidence_expires_at"],
        "daily_quota_units": 10000,
        "spend_cap_minor": 0,
    }
    try:
        selected = registry.choose(
            account_refs={"cloudflare": account_id},
            quota_evidence_by_model={MODEL_ID: registry_evidence},
            required_images=24,
            spend_cap_minor=0,
        )
    except Exception as exc:
        raise PapiKidsZeroSpendRuntimeError(
            f"Le registre refuse le modèle gratuit ({type(exc).__name__})."
        ) from exc
    if selected.get("provider_id") != "cloudflare" or selected.get("model_id") != MODEL_ID:
        raise PapiKidsZeroSpendRuntimeError("Le registre n'a pas sélectionné le modèle FLUX autorisé.")
    estimated_units = selected.get("estimated_units_per_image")
    if estimated_units != math.ceil(estimate_flux_schnell_neurons(1024, 1024, 4)):
        raise PapiKidsZeroSpendRuntimeError("Le coût du registre diffère de l'estimation FLUX vérifiée.")

    factory = connection_factory
    if factory is None and (reservation_store is None or asset_registrar is None):
        factory = create_postgres_connection_factory()
    if reservation_store is None:
        reservation_store = PostgresNeuronReservationStore(factory)
    if asset_registrar is None:
        asset_registrar = build_postgres_asset_registrar(factory)

    provider_kwargs = {
        "account_id": account_id,
        "api_token": api_token,
        "reservation_store": reservation_store,
    }
    if transport is not None:
        provider_kwargs["transport"] = transport
    provider = CloudflareFluxSchnellProvider(**provider_kwargs)
    batch_adapter = CloudflareFluxSchnellBatchAdapter(
        provider=provider,
        quota_evidence=evidence,
        generation_authorized=generation_authorized,
    )
    router = FreeImageModelRouter(
        provider=batch_adapter,
        models=[FreeImageModel(MODEL_ID, estimated_units, True)],
        max_batch_size=max_batch_size,
    )
    asset_center = PapiKidsIllustrationAssetCenter(
        root, asset_registrar=asset_registrar,
    )
    engine = ImageProductionEngine(
        generator=router, asset_center=asset_center, max_batch_size=max_batch_size,
    )
    return engine, {
        "upload_id": upload_id,
        "provider_id": "cloudflare",
        "model_id": MODEL_ID,
        "estimated_neurons_per_image": estimate_flux_schnell_neurons(1024, 1024, 4),
        "estimated_neurons_for_24_images": campaign_neurons,
        "quota_evidence_ref": evidence["evidence_ref"],
        "generation_authorized": generation_authorized,
        "network_called": False,
        "provider_calls": 0,
        "paid_fallback": False,
        "spend_cap_minor": 0,
        "asset_store": "private_papi_kids_store_plus_postgresql_registry",
        "print_ready_300dpi": False,
    }
