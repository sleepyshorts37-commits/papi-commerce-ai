"""Governed provider/model registry for PAPI image generation.

No provider or model is enabled by catalogue presence. An operator must supply
current account-specific quota evidence, commercial-use review and a zero-spend
policy before a model can be selected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .image_quota_evidence import QuotaEvidenceError, validate_quota_evidence


class ProviderRegistryError(ValueError):
    """Provider/model metadata is missing, stale, unsafe or not approved."""


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    display_name: str
    official_docs: str
    status: str
    api_mode: str
    default_enabled: bool = False


@dataclass(frozen=True)
class ModelProfile:
    provider_id: str
    model_id: str
    modality: str
    estimated_units_per_image: int
    commercial_use_reviewed: bool
    output_policy_reviewed: bool
    enabled: bool = False


PROVIDER_CATALOGUE = (
    ProviderProfile(
        provider_id="cloudflare",
        display_name="Cloudflare Workers AI",
        official_docs="https://developers.cloudflare.com/workers-ai/platform/pricing/",
        status="candidate_requires_account_verification",
        api_mode="account_api",
    ),
    ProviderProfile(
        provider_id="pollinations",
        display_name="Pollinations",
        official_docs="https://github.com/pollinations/pollinations/blob/master/APIDOCS.md",
        status="disabled_pending_terms_and_commercial_review",
        api_mode="public_api",
    ),
    ProviderProfile(
        provider_id="huggingface_zerogpu",
        display_name="Hugging Face ZeroGPU",
        official_docs="https://huggingface.co/docs/hub/spaces-zerogpu",
        status="disabled_experimental_space_not_production_api",
        api_mode="space",
    ),
)


class ImageProviderRegistry:
    """Runtime allowlist assembled from explicitly reviewed configuration."""

    def __init__(
        self,
        *,
        providers: Iterable[ProviderProfile] = PROVIDER_CATALOGUE,
        models: Iterable[ModelProfile] = (),
    ) -> None:
        self.providers = {item.provider_id: item for item in providers}
        self.models = {}
        for item in models:
            key = (item.provider_id, item.model_id)
            if key in self.models:
                raise ProviderRegistryError("Modèle dupliqué dans le registre.")
            if item.provider_id not in self.providers:
                raise ProviderRegistryError("Fournisseur absent du catalogue.")
            if item.modality != "image":
                raise ProviderRegistryError("Seuls les modèles image sont acceptés.")
            if (not isinstance(item.estimated_units_per_image, int)
                    or isinstance(item.estimated_units_per_image, bool)
                    or item.estimated_units_per_image <= 0):
                raise ProviderRegistryError("Coût estimé du modèle invalide.")
            self.models[key] = item

    def list_catalogue(self) -> list[dict[str, Any]]:
        return [
            {
                "provider_id": provider.provider_id,
                "display_name": provider.display_name,
                "official_docs": provider.official_docs,
                "status": provider.status,
                "api_mode": provider.api_mode,
                "default_enabled": provider.default_enabled,
                "models": [
                    {
                        "model_id": model.model_id,
                        "modality": model.modality,
                        "estimated_units_per_image": model.estimated_units_per_image,
                        "enabled": model.enabled,
                        "commercial_use_reviewed": model.commercial_use_reviewed,
                        "output_policy_reviewed": model.output_policy_reviewed,
                    }
                    for model in self.models.values()
                    if model.provider_id == provider.provider_id
                ],
            }
            for provider in self.providers.values()
        ]

    def eligible_models(
        self,
        *,
        account_refs: dict[str, str],
        quota_evidence_by_model: dict[str, dict[str, Any]],
        required_images: int,
        spend_cap_minor: int = 0,
    ) -> list[dict[str, Any]]:
        """Return only explicitly enabled models with fresh, matching proof.

        This is a policy filter, not a live provider API query. Provider-side
        reservation/commit is still mandatory before any actual generation.
        """
        if spend_cap_minor != 0:
            raise ProviderRegistryError("Le plafond de dépenses doit rester à zéro.")
        eligible = []
        for model in self.models.values():
            provider = self.providers[model.provider_id]
            if not provider.default_enabled or not model.enabled:
                continue
            if not model.commercial_use_reviewed or not model.output_policy_reviewed:
                continue
            account_ref = account_refs.get(model.provider_id)
            evidence = quota_evidence_by_model.get(model.model_id)
            if not account_ref or not evidence:
                continue
            try:
                quota = validate_quota_evidence(
                    evidence,
                    provider=model.provider_id,
                    account_ref=account_ref,
                    model_id=model.model_id,
                    estimated_units_per_image=model.estimated_units_per_image,
                    required_images=required_images,
                )
            except QuotaEvidenceError:
                continue
            eligible.append({
                "provider_id": model.provider_id,
                "model_id": model.model_id,
                "estimated_units_per_image": model.estimated_units_per_image,
                "estimated_campaign_units": quota["estimated_campaign_units"],
                "quota_evidence_ref": quota["evidence_ref"],
                "spend_cap_minor": 0,
            })
        return sorted(
            eligible,
            key=lambda item: (
                item["estimated_units_per_image"],
                item["provider_id"],
                item["model_id"],
            ),
        )

    def choose(
        self,
        *,
        account_refs: dict[str, str],
        quota_evidence_by_model: dict[str, dict[str, Any]],
        required_images: int,
        spend_cap_minor: int = 0,
    ) -> dict[str, Any]:
        eligible = self.eligible_models(
            account_refs=account_refs,
            quota_evidence_by_model=quota_evidence_by_model,
            required_images=required_images,
            spend_cap_minor=spend_cap_minor,
        )
        if not eligible:
            raise ProviderRegistryError(
                "Aucun modèle image actuellement autorisé avec quota vérifié. "
                "Aucun fallback payant ne sera tenté."
            )
        return eligible[0]
