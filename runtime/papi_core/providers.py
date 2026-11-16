"""Interfaces de génération PAPI KIDS ; aucun appel réseau ni fournisseur payant."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """Erreur de configuration, d'autorisation ou de génération."""


@dataclass(frozen=True)
class GenerationRequest:
    project_id: str
    kind: str
    prompt: str
    estimated_cost_xof: int = 0
    max_output_chars: int = 20000

    def validate(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip() or len(self.project_id) > 100:
            raise ProviderError("Identifiant de projet invalide.")
        if not isinstance(self.kind, str) or self.kind not in {"text", "image"}:
            raise ProviderError("Type de génération autorisé : text ou image.")
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ProviderError("Le prompt de génération est obligatoire.")
        if len(self.prompt) > 12000:
            raise ProviderError("Le prompt dépasse 12 000 caractères.")
        if (
            not isinstance(self.estimated_cost_xof, int)
            or isinstance(self.estimated_cost_xof, bool)
            or self.estimated_cost_xof < 0
        ):
            raise ProviderError("Estimation de coût invalide.")
        if (
            not isinstance(self.max_output_chars, int)
            or isinstance(self.max_output_chars, bool)
            or not 1 <= self.max_output_chars <= 100000
        ):
            raise ProviderError("Limite de sortie invalide.")


@dataclass(frozen=True)
class GenerationResult:
    provider: str
    kind: str
    content: str
    content_sha256: str
    estimated_cost_xof: int
    simulated: bool


class GenerationProvider(Protocol):
    name: str
    supported_kinds: frozenset[str]
    is_external: bool
    credentials_env: str | None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Exécute la génération selon le contrat du fournisseur."""


class MockGenerationProvider:
    """Fournisseur local déterministe de test ; ne produit aucun vrai contenu éditorial."""

    name = "mock"
    supported_kinds = frozenset({"text", "image"})
    is_external = False
    credentials_env = None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        request.validate()
        if request.estimated_cost_xof != 0:
            raise ProviderError("Le fournisseur mock doit rester gratuit.")
        digest = hashlib.sha256(
            f"{request.project_id}|{request.kind}|{request.prompt}".encode("utf-8")
        ).hexdigest()
        content = (
            f"[SIMULATION MOCK — aucun livrable réel généré]\n"
            f"type={request.kind}\nrequest_sha256={digest}"
        )[:request.max_output_chars]
        return GenerationResult(
            provider=self.name,
            kind=request.kind,
            content=content,
            content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            estimated_cost_xof=0,
            simulated=True,
        )


@dataclass(frozen=True)
class ProviderPolicy:
    """Garde-fous fermés par défaut pour tout connecteur externe."""

    allow_external: bool = False
    owner_approved: bool = False
    max_cost_xof: int = 0
    allowed_providers: frozenset[str] = frozenset({"mock"})

    def validate(self) -> None:
        if (
            not isinstance(self.max_cost_xof, int)
            or isinstance(self.max_cost_xof, bool)
            or self.max_cost_xof < 0
        ):
            raise ProviderError("Plafond de coût invalide.")
        if not isinstance(self.allow_external, bool) or not isinstance(self.owner_approved, bool):
            raise ProviderError("Les options d'autorisation doivent être booléennes.")
        if self.allow_external and not self.owner_approved:
            raise ProviderError("Un accord explicite du propriétaire est requis.")
        if (
            not isinstance(self.allowed_providers, (set, frozenset))
            or not self.allowed_providers
            or any(not isinstance(name, str) or not name.strip() for name in self.allowed_providers)
        ):
            raise ProviderError("Registre de fournisseurs autorisés invalide.")


class ProviderRegistry:
    """Registre en mémoire : aucun fournisseur externe n'est activé implicitement."""

    def __init__(self, policy: ProviderPolicy | None = None):
        self.policy = policy or ProviderPolicy()
        self.policy.validate()
        self._providers: dict[str, GenerationProvider] = {}
        self.register(MockGenerationProvider())

    def register(self, provider: GenerationProvider) -> None:
        if not isinstance(provider.name, str) or not provider.name.strip() or provider.name in self._providers:
            raise ProviderError("Nom de fournisseur absent ou déjà enregistré.")
        if not provider.supported_kinds or not provider.supported_kinds.issubset({"text", "image"}):
            raise ProviderError("Capacités de fournisseur invalides.")
        self._providers[provider.name] = provider

    def generate(self, provider_name: str, request: GenerationRequest) -> GenerationResult:
        request.validate()
        self.policy.validate()
        provider = self._providers.get(provider_name)
        if provider is None or provider_name not in self.policy.allowed_providers:
            raise ProviderError("Fournisseur non autorisé ou non enregistré.")
        if request.kind not in provider.supported_kinds:
            raise ProviderError("Ce fournisseur ne prend pas en charge ce type de génération.")
        if request.estimated_cost_xof > self.policy.max_cost_xof:
            raise ProviderError("Plafond de coût dépassé : génération bloquée.")
        if provider.is_external:
            if not self.policy.allow_external or not self.policy.owner_approved:
                raise ProviderError("Les appels externes sont désactivés sans accord explicite.")
            if not provider.credentials_env or not os.environ.get(provider.credentials_env):
                raise ProviderError("Secret fournisseur absent de l'environnement.")
        result = provider.generate(request)
        if result.estimated_cost_xof > self.policy.max_cost_xof:
            raise ProviderError("Le coût retourné dépasse le plafond autorisé.")
        return result
