"""Passerelle commune PAPI CONNECT, avec adaptateur simulé uniquement."""
from __future__ import annotations

from typing import Protocol

from papi_core.provider_registry import (
    DEFAULT_CATALOG, ProviderRegistryError, authorize_provider, load_provider_catalog,
)
from papi_core.providers import (
    GenerationProvider, GenerationRequest, GenerationResult, MockGenerationProvider,
    ProviderError,
)

class ConnectorError(RuntimeError):
    """Erreur d’accès ou d’exécution d’un connecteur."""

class ConnectorAdapter(Protocol):
    name: str
    supported_kinds: frozenset[str]
    is_external: bool
    credentials_env: str | None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Exécute une génération conforme au contrat commun."""

class ConnectorGateway:
    """Relie le catalogue de fournisseurs au registre d’adaptateurs.

    Aucun appel réseau n’est effectué par cette passerelle. Les adaptateurs
    externes restent bloqués dans cette mission.
    """

    def __init__(self, catalog_path=DEFAULT_CATALOG):
        self.catalog_path = catalog_path
        self._adapters: dict[str, ConnectorAdapter] = {
            "local.mock": MockGenerationProvider(),
        }

    def register_adapter(self, provider_id: str, adapter: ConnectorAdapter) -> None:
        if not provider_id or provider_id in self._adapters:
            raise ConnectorError("Identifiant d’adaptateur absent ou déjà enregistré.")
        if not adapter.name or not adapter.supported_kinds:
            raise ConnectorError("Contrat d’adaptateur incomplet.")
        if not adapter.supported_kinds.issubset({"text", "image"}):
            raise ConnectorError("Type de génération non pris en charge.")
        self._adapters[provider_id] = adapter

    def generate(self, provider_id: str, request: GenerationRequest, agent_permissions: set[str]) -> GenerationResult:
        request.validate()
        try:
            catalog = load_provider_catalog(self.catalog_path)
            provider = next((item for item in catalog["providers"] if item["id"] == provider_id), None)
            if provider is None:
                raise ConnectorError("Fournisseur absent du catalogue.")
            authorize_provider(provider, agent_permissions)
            if provider["external"]:
                raise ConnectorError("Les connecteurs externes sont bloqués dans la Mission 184.")
            adapter = self._adapters.get(provider_id)
            if adapter is None:
                raise ConnectorError("Aucun adaptateur installé pour ce fournisseur.")
            if adapter.is_external:
                raise ConnectorError("Un adaptateur externe ne peut pas être exécuté dans cette mission.")
            expected_capability = "text.generate" if request.kind == "text" else "image.generate"
            if expected_capability not in provider["capabilities"]:
                raise ConnectorError("Capacité absente du catalogue fournisseur.")
            if request.kind not in adapter.supported_kinds:
                raise ConnectorError("Type de génération non pris en charge par l’adaptateur.")
            if request.estimated_cost_xof > provider["quota"]["max_cost_xof"]:
                raise ConnectorError("Plafond fournisseur dépassé : opération bloquée.")
            result = adapter.generate(request)
            if result.estimated_cost_xof > provider["quota"]["max_cost_xof"]:
                raise ConnectorError("Le coût retourné dépasse le plafond fournisseur.")
            return result
        except ProviderRegistryError as exc:
            raise ConnectorError(str(exc)) from exc
        except ProviderError as exc:
            raise ConnectorError(str(exc)) from exc
