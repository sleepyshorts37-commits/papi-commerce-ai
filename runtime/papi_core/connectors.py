"""Passerelle commune PAPI CONNECT, avec adaptateur simulé uniquement."""
from __future__ import annotations

import hashlib
from typing import Protocol

from papi_core.provider_registry import (
    DEFAULT_CATALOG, ProviderRegistryError, authorize_provider, load_provider_catalog,
)
from papi_core.providers import (
    GenerationRequest, GenerationResult, MockGenerationProvider, ProviderError,
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

    La passerelle n'effectue elle-même aucun appel réseau. Seuls des adaptateurs
    locaux de confiance peuvent être enregistrés dans cette version ; tout
    adaptateur externe ou porteur de credentials reste refusé.
    """

    def __init__(self, catalog_path=DEFAULT_CATALOG):
        self.catalog_path = catalog_path
        self._adapters: dict[str, ConnectorAdapter] = {
            "local.mock": MockGenerationProvider(),
        }

    def register_adapter(self, provider_id: str, adapter: ConnectorAdapter) -> None:
        if not isinstance(provider_id, str) or not provider_id.strip() or provider_id in self._adapters:
            raise ConnectorError("Identifiant d’adaptateur absent ou déjà enregistré.")
        name = getattr(adapter, "name", None)
        supported_kinds = getattr(adapter, "supported_kinds", None)
        is_external = getattr(adapter, "is_external", None)
        credentials_env = getattr(adapter, "credentials_env", None)
        if not isinstance(name, str) or not name.strip():
            raise ConnectorError("Nom d’adaptateur absent.")
        if not isinstance(supported_kinds, (set, frozenset)) or not supported_kinds:
            raise ConnectorError("Capacités d’adaptateur absentes ou invalides.")
        if any(kind not in {"text", "image"} for kind in supported_kinds):
            raise ConnectorError("Type de génération non pris en charge.")
        if not isinstance(is_external, bool) or is_external:
            raise ConnectorError("Les adaptateurs externes ne sont pas enregistrables dans cette mission.")
        if credentials_env is not None:
            raise ConnectorError("Un adaptateur local ne doit déclarer aucun credential.")
        if not callable(getattr(adapter, "generate", None)):
            raise ConnectorError("Fonction d'exécution d'adaptateur absente ou invalide.")
        self._adapters[provider_id] = adapter

    @staticmethod
    def _validate_result(
        provider_id: str,
        adapter: ConnectorAdapter,
        request: GenerationRequest,
        result: GenerationResult,
        max_cost_xof: int,
    ) -> None:
        if not isinstance(result, GenerationResult):
            raise ConnectorError("Résultat fournisseur incompatible avec le contrat commun.")
        if result.provider != adapter.name:
            raise ConnectorError("Identité du fournisseur retourné incohérente.")
        if result.kind != request.kind:
            raise ConnectorError("Type du résultat différent de la requête.")
        if not isinstance(result.content, str) or not result.content:
            raise ConnectorError("Contenu fournisseur absent ou invalide.")
        if len(result.content) > request.max_output_chars:
            raise ConnectorError("Le résultat dépasse la limite de sortie demandée.")
        expected_digest = hashlib.sha256(result.content.encode("utf-8")).hexdigest()
        if not isinstance(result.content_sha256, str) or result.content_sha256 != expected_digest:
            raise ConnectorError("Empreinte SHA-256 du résultat invalide.")
        if (
            not isinstance(result.estimated_cost_xof, int)
            or isinstance(result.estimated_cost_xof, bool)
            or result.estimated_cost_xof < 0
        ):
            raise ConnectorError("Coût retourné invalide.")
        if result.estimated_cost_xof > max_cost_xof:
            raise ConnectorError("Le coût retourné dépasse le plafond fournisseur.")
        if not isinstance(result.simulated, bool):
            raise ConnectorError("Indicateur de simulation invalide.")
        if provider_id == "local.mock" and (
            result.simulated is not True or not result.content.startswith("[SIMULATION MOCK")
        ):
            raise ConnectorError("Le connecteur mock doit rester explicitement simulé.")

    def generate(
        self,
        provider_id: str,
        request: GenerationRequest,
        agent_permissions: set[str],
    ) -> GenerationResult:
        try:
            request.validate()
            if not isinstance(agent_permissions, (set, frozenset)) or any(
                not isinstance(permission, str) for permission in agent_permissions
            ):
                raise ConnectorError("Ensemble de permissions d’agent invalide.")
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
            max_cost_xof = provider["quota"]["max_cost_xof"]
            if request.estimated_cost_xof > max_cost_xof:
                raise ConnectorError("Plafond fournisseur dépassé : opération bloquée.")
            adapter_failed = False
            try:
                result = adapter.generate(request)
            except Exception:
                # Ne pas conserver l'exception fournisseur dans __context__.
                # Aucun retry automatique : l'appelant doit réconcilier un résultat incertain.
                adapter_failed = True
            if adapter_failed:
                raise ConnectorError("Échec d'exécution de l'adaptateur.")

            validation_failed = False
            try:
                self._validate_result(provider_id, adapter, request, result, max_cost_xof)
            except ConnectorError:
                raise
            except Exception:
                # Lever après le bloc except évite de conserver le diagnostic interne.
                validation_failed = True
            if validation_failed:
                raise ConnectorError("Résultat d'adaptateur invalide.")
            return result
        except ConnectorError:
            raise
        except ProviderRegistryError as exc:
            raise ConnectorError(str(exc)) from exc
        except ProviderError as exc:
            raise ConnectorError(str(exc)) from exc
