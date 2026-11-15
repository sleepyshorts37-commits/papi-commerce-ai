"""Cloudflare Workers AI image adapter and conservative daily quota ledger.

The ledger is process-local. It is a safety guard for one process, not an
authoritative Cloudflare account-usage meter or a cross-worker transaction store.
No network call occurs until generate() is explicitly invoked.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
import re
import threading
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ImageProviderError(RuntimeError):
    """Provider configuration, quota, or generation failure."""


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$")
DEFAULT_DAILY_NEURON_LIMIT = 10_000


@dataclass(frozen=True)
class QuotaReservation:
    reservation_id: str
    idempotency_key: str
    utc_day: str
    estimated_neurons: int
    status: str


class InMemoryNeuronQuotaLedger:
    """Thread-safe, UTC-day quota ledger with idempotent reservations."""

    def __init__(self, daily_limit: int = DEFAULT_DAILY_NEURON_LIMIT) -> None:
        if not isinstance(daily_limit, int) or isinstance(daily_limit, bool) or daily_limit <= 0:
            raise ImageProviderError("La limite quotidienne doit être un entier positif.")
        self.daily_limit = daily_limit
        self._lock = threading.RLock()
        self._reservations: dict[str, QuotaReservation] = {}
        self._used_by_day: dict[str, int] = {}
        self._reserved_by_day: dict[str, int] = {}

    @staticmethod
    def _today(now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ImageProviderError("L'horodatage du quota doit inclure un fuseau horaire.")
        return current.astimezone(timezone.utc).date().isoformat()

    def reserve(
        self, *, idempotency_key: str, estimated_neurons: int,
        now: datetime | None = None, model: str | None = None,
    ) -> QuotaReservation:
        if not isinstance(idempotency_key, str) or not IDENTIFIER.fullmatch(idempotency_key):
            raise ImageProviderError("Clé d'idempotence invalide.")
        if not isinstance(estimated_neurons, int) or isinstance(estimated_neurons, bool) or estimated_neurons <= 0:
            raise ImageProviderError("Estimation de consommation invalide.")
        day = self._today(now)
        with self._lock:
            existing = self._reservations.get(idempotency_key)
            if existing:
                if existing.utc_day != day or existing.estimated_neurons != estimated_neurons:
                    raise ImageProviderError("Clé d'idempotence déjà utilisée avec un autre jour ou coût.")
                return existing
            used = self._used_by_day.get(day, 0)
            reserved = self._reserved_by_day.get(day, 0)
            if used + reserved + estimated_neurons > self.daily_limit:
                raise ImageProviderError("Quota quotidien insuffisant : génération bloquée avant appel fournisseur.")
            reservation = QuotaReservation(
                reservation_id=f"CFQ-{day}-{len(self._reservations) + 1}",
                idempotency_key=idempotency_key,
                utc_day=day,
                estimated_neurons=estimated_neurons,
                status="reserved",
            )
            self._reservations[idempotency_key] = reservation
            self._reserved_by_day[day] = reserved + estimated_neurons
            return reservation

    def commit(self, reservation: QuotaReservation, actual_neurons: int | None = None) -> QuotaReservation:
        actual = reservation.estimated_neurons if actual_neurons is None else actual_neurons
        if not isinstance(actual, int) or isinstance(actual, bool) or actual <= 0:
            raise ImageProviderError("Consommation réelle invalide.")
        with self._lock:
            current = self._reservations.get(reservation.idempotency_key)
            if current is None or current.reservation_id != reservation.reservation_id:
                raise ImageProviderError("Réservation inconnue.")
            if current.status == "committed":
                return current
            if current.status != "reserved":
                raise ImageProviderError("Réservation déjà clôturée.")
            day = current.utc_day
            reserved = self._reserved_by_day.get(day, 0) - current.estimated_neurons
            used = self._used_by_day.get(day, 0)
            if used + actual > self.daily_limit:
                raise ImageProviderError("Consommation réelle supérieure au quota réservé : réconciliation requise.")
            self._reserved_by_day[day] = max(0, reserved)
            self._used_by_day[day] = used + actual
            committed = QuotaReservation(
                current.reservation_id, current.idempotency_key, day, actual, "committed"
            )
            self._reservations[current.idempotency_key] = committed
            return committed

    def release(self, reservation: QuotaReservation) -> QuotaReservation:
        with self._lock:
            current = self._reservations.get(reservation.idempotency_key)
            if current is None or current.reservation_id != reservation.reservation_id:
                raise ImageProviderError("Réservation inconnue.")
            if current.status == "released":
                return current
            if current.status != "reserved":
                raise ImageProviderError("Impossible de libérer une réservation déjà consommée.")
            day = current.utc_day
            self._reserved_by_day[day] = max(
                0, self._reserved_by_day.get(day, 0) - current.estimated_neurons
            )
            released = QuotaReservation(
                current.reservation_id, current.idempotency_key, day,
                current.estimated_neurons, "released"
            )
            self._reservations[current.idempotency_key] = released
            return released

    def snapshot(self, now: datetime | None = None) -> dict[str, int | str]:
        day = self._today(now)
        with self._lock:
            used = self._used_by_day.get(day, 0)
            reserved = self._reserved_by_day.get(day, 0)
            return {
                "utc_day": day, "daily_limit": self.daily_limit,
                "used_estimated_neurons": used,
                "reserved_estimated_neurons": reserved,
                "available_estimated_neurons": max(0, self.daily_limit - used - reserved),
            }


class SupabaseNeuronQuotaLedger:
    """Persistent shared quota ledger using the Mission 104 PostgREST RPCs."""
    def __init__(self, *, supabase_url: str, service_role_key: str,
                 account_ref: str, worker_id: str,
                 daily_limit: int = DEFAULT_DAILY_NEURON_LIMIT,
                 timeout_seconds: int = 15) -> None:
        if not isinstance(supabase_url, str) or not supabase_url.startswith("https://"):
            raise ImageProviderError("URL Supabase HTTPS invalide.")
        if not isinstance(service_role_key, str) or not service_role_key.strip():
            raise ImageProviderError("Clé serveur Supabase absente.")
        if not isinstance(account_ref, str) or not IDENTIFIER.fullmatch(account_ref):
            raise ImageProviderError("Référence de compte fournisseur invalide.")
        if not isinstance(worker_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,119}", worker_id):
            raise ImageProviderError("Identifiant du worker invalide.")
        if not isinstance(daily_limit, int) or isinstance(daily_limit, bool) or daily_limit <= 0:
            raise ImageProviderError("Plafond quotidien Supabase invalide.")
        if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 60:
            raise ImageProviderError("Délai Supabase invalide.")
        self.rpc_root = supabase_url.rstrip("/") + "/rest/v1/rpc/"
        self.key = service_role_key
        self.account_ref = account_ref
        self.worker_id = worker_id
        self.daily_limit = daily_limit
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "SupabaseNeuronQuotaLedger":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            account_ref=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
            worker_id=os.getenv("PAPI_WORKER_ID", "PAPI-IMAGE-01"),
            daily_limit=int(os.getenv("PAPI_CLOUDFLARE_DAILY_NEURON_LIMIT", str(DEFAULT_DAILY_NEURON_LIMIT))),
        )

    def _rpc(self, function: str, payload: dict[str, Any]) -> Any:
        request = Request(self.rpc_root + function, data=json.dumps(payload).encode("utf-8"),
            headers={"apikey": self.key, "Authorization": "Bearer " + self.key,
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            raise ImageProviderError(f"Échec RPC Supabase ({exc.code}).") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ImageProviderError("Connexion Supabase incertaine ; ne pas relancer automatiquement.") from exc
        try:
            return json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImageProviderError("Réponse RPC Supabase illisible.") from exc

    @staticmethod
    def _row(payload: Any) -> dict[str, Any]:
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return payload[0]
        if isinstance(payload, dict):
            return payload
        raise ImageProviderError("Réponse RPC Supabase incomplète.")

    def reserve(self, *, idempotency_key: str, estimated_neurons: int,
                now: datetime | None = None, model: str | None = None) -> QuotaReservation:
        if not isinstance(model, str) or not IDENTIFIER.fullmatch(model):
            raise ImageProviderError("Modèle requis pour le registre partagé.")
        if not isinstance(idempotency_key, str) or not re.fullmatch(r"[A-Za-z0-9:_./-]{8,180}", idempotency_key):
            raise ImageProviderError("Clé d'idempotence Supabase invalide.")
        if not isinstance(estimated_neurons, int) or isinstance(estimated_neurons, bool) or estimated_neurons <= 0:
            raise ImageProviderError("Estimation de consommation invalide.")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ImageProviderError("L'horodatage du quota doit inclure un fuseau horaire.")
        day = current.astimezone(timezone.utc).date().isoformat()
        row = self._row(self._rpc("papi_reserve_provider_quota", {
            "p_idempotency_key": idempotency_key, "p_provider": "cloudflare",
            "p_account_ref": self.account_ref, "p_model": model,
            "p_worker_id": self.worker_id, "p_estimated_units": estimated_neurons,
            "p_daily_limit": self.daily_limit, "p_quota_day": day}))
        return QuotaReservation(str(row["reservation_id"]), idempotency_key,
            str(row["quota_day"]), estimated_neurons, str(row["reservation_status"]))

    def commit(self, reservation: QuotaReservation,
               actual_neurons: int | None = None) -> QuotaReservation:
        actual = reservation.estimated_neurons if actual_neurons is None else actual_neurons
        if not isinstance(actual, int) or isinstance(actual, bool) or actual <= 0:
            raise ImageProviderError("Consommation réelle invalide.")
        self._rpc("papi_commit_provider_quota", {
            "p_reservation_id": reservation.reservation_id, "p_actual_units": actual})
        return QuotaReservation(reservation.reservation_id, reservation.idempotency_key,
            reservation.utc_day, actual, "committed")

    def mark_uncertain(self, reservation: QuotaReservation) -> None:
        self._rpc("papi_mark_provider_quota_uncertain", {
            "p_reservation_id": reservation.reservation_id})

    def release(self, reservation: QuotaReservation) -> QuotaReservation:
        self._rpc("papi_release_provider_quota", {
            "p_reservation_id": reservation.reservation_id})
        return QuotaReservation(reservation.reservation_id, reservation.idempotency_key,
            reservation.utc_day, reservation.estimated_neurons, "released")


class CloudflareImageAdapter:
    """Explicit Cloudflare REST adapter; no implicit retries or paid fallback."""

    API_ROOT = "https://api.cloudflare.com/client/v4/accounts"

    def __init__(
        self, *, account_id: str, api_token: str,
        ledger: Any,
        model_costs: dict[str, int],
        free_tier_confirmed_for_account: bool,
        transport: Callable[..., Any] | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        if not isinstance(account_id, str) or not IDENTIFIER.fullmatch(account_id):
            raise ImageProviderError("Identifiant de compte Cloudflare invalide.")
        if not isinstance(api_token, str) or not api_token.strip():
            raise ImageProviderError("Jeton Cloudflare absent de l'environnement serveur.")
        if free_tier_confirmed_for_account is not True:
            raise ImageProviderError("Statut gratuit du compte non confirmé : fournisseur bloqué.")
        if not isinstance(model_costs, dict) or not model_costs:
            raise ImageProviderError("Aucun coût estimé de modèle explicitement configuré.")
        for model, cost in model_costs.items():
            if not isinstance(model, str) or not IDENTIFIER.fullmatch(model):
                raise ImageProviderError("Identifiant de modèle invalide.")
            if not isinstance(cost, int) or isinstance(cost, bool) or cost <= 0:
                raise ImageProviderError("Chaque modèle doit avoir un coût estimé positif connu.")
        if not all(callable(getattr(ledger, method, None)) for method in ("reserve", "commit", "release")):
            raise ImageProviderError("Ledger de quotas PAPI incompatible.")
        if not isinstance(timeout_seconds, int) or timeout_seconds < 1 or timeout_seconds > 180:
            raise ImageProviderError("Délai réseau invalide.")
        self.account_id = account_id
        self._api_token = api_token
        self.ledger = ledger
        self.model_costs = dict(model_costs)
        self.timeout_seconds = timeout_seconds
        self._transport = transport or self._https_transport

    @classmethod
    def from_environment(
        cls, *, ledger: InMemoryNeuronQuotaLedger, model_costs: dict[str, int],
        free_tier_confirmed_for_account: bool, transport: Callable[..., Any] | None = None,
    ) -> "CloudflareImageAdapter":
        return cls(
            account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
            api_token=os.getenv("CLOUDFLARE_API_TOKEN", ""),
            ledger=ledger, model_costs=model_costs,
            free_tier_confirmed_for_account=free_tier_confirmed_for_account,
            transport=transport,
        )

    @classmethod
    def from_shared_environment(
        cls, *, model_costs: dict[str, int], free_tier_confirmed_for_account: bool,
        transport: Callable[..., Any] | None = None,
    ) -> "CloudflareImageAdapter":
        """Build the Cloudflare adapter with the cross-worker Supabase ledger."""
        ledger = SupabaseNeuronQuotaLedger.from_environment()
        return cls.from_environment(
            ledger=ledger, model_costs=model_costs,
            free_tier_confirmed_for_account=free_tier_confirmed_for_account,
            transport=transport,
        )

    @staticmethod
    def _https_transport(url: str, *, headers: dict[str, str], json_body: dict[str, Any], timeout: int):
        import json
        body = json.dumps(json_body).encode("utf-8")
        request = Request(url, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            return response

    def generate(
        self, *, prompt: str, model: str, idempotency_key: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
            raise ImageProviderError("Prompt vide ou trop volumineux.")
        if model not in self.model_costs:
            raise ImageProviderError("Modèle non autorisé ou coût inconnu : aucun appel effectué.")
        reservation = self.ledger.reserve(
            idempotency_key=idempotency_key,
            estimated_neurons=self.model_costs[model], now=now, model=model,
        )
        if reservation.status == "committed":
            raise ImageProviderError("Cette mission a déjà été exécutée ; résultat non conservé par cet adaptateur.")
        if reservation.status != "reserved":
            raise ImageProviderError("Réservation non utilisable.")
        url = f"{self.API_ROOT}/{self.account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
        try:
            response = self._transport(
                url, headers=headers, json_body={"prompt": prompt.strip()},
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            # Timeout/network failure is ambiguous: retain reservation to avoid
            # accidentally double-spending a quota after a provider-side success.
            if callable(getattr(self.ledger, "mark_uncertain", None)):
                try:
                    self.ledger.mark_uncertain(reservation)
                except Exception:
                    pass
            raise ImageProviderError(
                "Échec réseau ambigu ; quota réservé conservé pour réconciliation. Aucun retry automatique."
            ) from exc
        status = getattr(response, "status_code", None)
        if status is None:
            status = getattr(response, "status", None)
        if not isinstance(status, int) or status < 200 or status >= 300:
            # A non-2xx response is treated conservatively as consumed/unknown.
            if callable(getattr(self.ledger, "mark_uncertain", None)):
                try:
                    self.ledger.mark_uncertain(reservation)
                except Exception:
                    pass
            raise ImageProviderError("Réponse fournisseur non concluante ; quota réservé conservé.")
        content = getattr(response, "content", None)
        if content is None and callable(getattr(response, "read", None)):
            content = response.read()
        if not isinstance(content, (bytes, bytearray)) or not content:
            raise ImageProviderError("Réponse image vide/invalide ; quota réservé conservé.")
        try:
            self.ledger.commit(reservation)
        except Exception as exc:
            if callable(getattr(self.ledger, "mark_uncertain", None)):
                try:
                    self.ledger.mark_uncertain(reservation)
                except Exception:
                    pass
            raise ImageProviderError("Image reçue mais validation du quota échouée ; réservation conservée pour rapprochement.") from exc
        return {
            "provider": "cloudflare_workers_ai",
            "model": model,
            "content_type": getattr(response, "headers", {}).get("content-type", "application/octet-stream"),
            "image_bytes": bytes(content),
            "estimated_neurons_committed": reservation.estimated_neurons,
            "quota_day_utc": reservation.utc_day,
            "paid_fallback_used": False,
        }
