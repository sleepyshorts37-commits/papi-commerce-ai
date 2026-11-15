"""Zero-spend guarded Cloudflare Workers AI FLUX.1 schnell adapter."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .papi_kids_asset_store import inspect_image

MODEL_ID = "@cf/black-forest-labs/flux-1-schnell"
PROVIDER_ID = "cloudflare_workers_ai"
FREE_DAILY_NEURONS = 10000.0
SOURCE_PRICING = "https://developers.cloudflare.com/workers-ai/platform/pricing"
SOURCE_MODEL = "https://developers.cloudflare.com/workers-ai/models/flux-1-schnell"


class ImageProviderBlocked(RuntimeError):
    """Provider execution was blocked by the zero-spend policy or quota gate."""


def estimate_flux_schnell_neurons(width_px: int = 1024, height_px: int = 1024, steps: int = 4) -> float:
    if not isinstance(width_px, int) or not isinstance(height_px, int) or width_px < 1 or height_px < 1:
        raise ValueError("Dimensions de sortie invalides.")
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 8:
        raise ValueError("FLUX schnell accepte 1 à 8 étapes.")
    tiles = math.ceil(width_px / 512) * math.ceil(height_px / 512)
    return round(tiles * 4.8 + steps * 9.6, 2)


def validate_free_quota_evidence(evidence: dict[str, Any], *, required_neurons: float,
                                 now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not isinstance(evidence, dict):
        raise ImageProviderBlocked("Preuve de quota gratuit absente.")
    if evidence.get("provider") != PROVIDER_ID or evidence.get("model_id") != MODEL_ID:
        raise ImageProviderBlocked("Fournisseur ou modèle non autorisé.")
    if evidence.get("account_plan") != "workers_free":
        raise ImageProviderBlocked("Seul le plan Workers Free est accepté ; aucun plan payant.")
    if evidence.get("daily_limit_neurons") != FREE_DAILY_NEURONS:
        raise ImageProviderBlocked("Plafond quotidien gratuit non confirmé.")
    if evidence.get("model_access_confirmed") is not True:
        raise ImageProviderBlocked("Disponibilité du modèle sur ce compte non confirmée.")
    if evidence.get("commercial_license_confirmed") is not True:
        raise ImageProviderBlocked("Licence commerciale du modèle non confirmée.")
    if evidence.get("zero_spend_confirmed") is not True or evidence.get("cost_limit_minor") != 0:
        raise ImageProviderBlocked("Autorisation de dépense nulle obligatoire.")
    if not evidence.get("evidence_ref") or not evidence.get("account_fingerprint"):
        raise ImageProviderBlocked("Référence de preuve ou empreinte de compte absente.")
    if not isinstance(evidence.get("account_fingerprint"), str) or not re.fullmatch(r"[0-9a-f]{64}", evidence["account_fingerprint"]):
        raise ImageProviderBlocked("Empreinte de compte invalide.")
    try:
        checked = datetime.fromisoformat(evidence["quota_checked_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(evidence["evidence_expires_at"].replace("Z", "+00:00"))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ImageProviderBlocked("Dates de preuve de quota invalides.") from exc
    if checked.tzinfo is None or expires.tzinfo is None:
        raise ImageProviderBlocked("Dates de preuve sans fuseau horaire.")
    if checked > now or (now - checked).total_seconds() > 24 * 3600 or expires <= now or (expires - checked).total_seconds() > 24 * 3600:
        raise ImageProviderBlocked("Preuve de quota périmée ; actualiser depuis le tableau de bord Cloudflare.")
    if checked.date() != now.date() or evidence.get("usage_date") != now.date().isoformat():
        raise ImageProviderBlocked("La preuve doit correspondre à la journée UTC courante.")
    remaining = evidence.get("remaining_neurons")
    if not isinstance(remaining, (int, float)) or remaining < required_neurons:
        raise ImageProviderBlocked("Quota gratuit restant insuffisant pour cette image.")


def _https_transport(url: str, headers: dict[str, str], payload: bytes, timeout: int = 90) -> tuple[int, bytes]:
    if not url.startswith("https://api.cloudflare.com/"):
        raise ImageProviderBlocked("Endpoint fournisseur non autorisé.")
    request = Request(url, data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(25 * 1024 * 1024)
    except HTTPError as exc:
        return exc.code, exc.read(1024 * 1024)
    except URLError as exc:
        raise ImageProviderBlocked("Échec réseau fournisseur ; aucun fallback payant.") from exc


class PostgresNeuronReservationStore:
    """Transactional daily usage ledger; injected with a server-side DB-API factory."""

    daily_limit = 10000

    def __init__(self, connection_factory: Callable[[], Any]):
        self.connection_factory = connection_factory

    def reserve(self, evidence: dict[str, Any], *, neurons: float, request_key: str,
                campaign_id: str, page_number: int, prompt_sha256: str) -> str:
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                insert into papi_kids_private.provider_daily_usage(
                    account_fingerprint, provider, model_id, usage_date, plan_type,
                    daily_limit_neurons, evidence_ref, quota_checked_at, evidence_expires_at
                ) values (%s,%s,%s,%s,'workers_free',10000,%s,%s,%s)
                on conflict (account_fingerprint, provider, model_id, usage_date)
                do update set evidence_ref = excluded.evidence_ref,
                              quota_checked_at = excluded.quota_checked_at,
                              evidence_expires_at = excluded.evidence_expires_at,
                              updated_at = now()
                """,
                (evidence["account_fingerprint"], PROVIDER_ID, MODEL_ID, evidence["usage_date"],
                 evidence["evidence_ref"], evidence["quota_checked_at"], evidence["evidence_expires_at"]),
            )
            cursor.execute(
                """select daily_limit_neurons, used_neurons, reserved_neurons
                     from papi_kids_private.provider_daily_usage
                    where account_fingerprint = %s and provider = %s and model_id = %s and usage_date = %s
                    for update""",
                (evidence["account_fingerprint"], PROVIDER_ID, MODEL_ID, evidence["usage_date"]),
            )
            row = cursor.fetchone()
            if not row or float(row[1]) + float(row[2]) + neurons > float(row[0]):
                raise ImageProviderBlocked("Ledger partagé : quota quotidien déjà réservé ou épuisé.")
            cursor.execute(
                """insert into papi_kids_private.provider_generation_reservations(
                    account_fingerprint, provider, model_id, usage_date, request_key,
                    campaign_id, page_number, prompt_sha256, reserved_neurons, cost_minor
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
                on conflict (request_key) do nothing
                returning reservation_id""",
                (evidence["account_fingerprint"], PROVIDER_ID, MODEL_ID, evidence["usage_date"],
                 request_key, campaign_id, page_number, prompt_sha256, neurons),
            )
            reservation = cursor.fetchone()
            if not reservation:
                raise ImageProviderBlocked("Cette demande a déjà été réservée ; génération répétée bloquée.")
            cursor.execute(
                """update papi_kids_private.provider_daily_usage
                      set reserved_neurons = reserved_neurons + %s, updated_at = now()
                    where account_fingerprint = %s and provider = %s and model_id = %s and usage_date = %s""",
                (neurons, evidence["account_fingerprint"], PROVIDER_ID, MODEL_ID, evidence["usage_date"]),
            )
            connection.commit()
            return str(reservation[0])
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()

    def settle(self, evidence: dict[str, Any], *, reservation_id: str,
               neurons: float, output_sha256: str | None, consumed: bool) -> None:
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """update papi_kids_private.provider_generation_reservations
                      set status = %s, output_sha256 = %s, settled_at = now()
                    where reservation_id = %s and status = 'reserved'
                    returning reserved_neurons""",
                ("completed" if output_sha256 else ("failed_consumed" if consumed else "released"),
                 output_sha256, reservation_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ImageProviderBlocked("Réservation introuvable ou déjà soldée.")
            reserved = float(row[0])
            cursor.execute(
                """update papi_kids_private.provider_daily_usage
                      set reserved_neurons = greatest(0, reserved_neurons - %s),
                          used_neurons = used_neurons + %s,
                          updated_at = now()
                    where account_fingerprint = %s and provider = %s and model_id = %s and usage_date = %s""",
                (reserved, reserved if consumed else 0,
                 evidence["account_fingerprint"], PROVIDER_ID, MODEL_ID, evidence["usage_date"]),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()


class CloudflareFluxSchnellProvider:
    """Single-model provider. It has no fallback, upgrade, or paid route."""

    def __init__(self, *, account_id: str, api_token: str,
                 reservation_store: PostgresNeuronReservationStore,
                 transport: Callable[[str, dict[str, str], bytes], tuple[int, bytes]] = _https_transport):
        if not isinstance(account_id, str) or not re.fullmatch(r'[a-f0-9]{32}', account_id) or not api_token:
            raise ImageProviderBlocked("Identifiants Cloudflare serveur absents.")
        self.account_id = account_id
        self.api_token = api_token
        self.reservation_store = reservation_store
        self.transport = transport

    def generate(self, prompt: str, *, evidence: dict[str, Any], allow_generation: bool,
                 campaign_id: str, page_number: int, steps: int = 4) -> dict[str, Any]:
        if allow_generation is not True:
            raise ImageProviderBlocked("Génération externe non autorisée.")
        if not isinstance(prompt, str) or not 1 <= len(prompt) <= 2048:
            raise ImageProviderBlocked("Prompt FLUX invalide.")
        if not isinstance(campaign_id, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', campaign_id) or not isinstance(page_number, int) or isinstance(page_number, bool) or not 1 <= page_number <= 200:
            raise ImageProviderBlocked("Référence de campagne ou numéro de page invalide.")
        neurons = estimate_flux_schnell_neurons(1024, 1024, steps)
        validate_free_quota_evidence(evidence, required_neurons=neurons)
        prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        request_key = hashlib.sha256(
            f"{evidence['account_fingerprint']}|{evidence['usage_date']}|{campaign_id}|{page_number}|{prompt_sha}".encode()
        ).hexdigest()
        reservation_id = self.reservation_store.reserve(
            evidence, neurons=neurons, request_key=request_key,
            campaign_id=campaign_id, page_number=page_number, prompt_sha256=prompt_sha,
        )
        sent = False
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{MODEL_ID}"
            payload = json.dumps({"prompt": prompt, "steps": steps}).encode("utf-8")
            sent = True
            status, body = self.transport(url, {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }, payload)
            if status != 200:
                raise ImageProviderBlocked(f"Cloudflare a refusé la requête (HTTP {status}); aucun fallback ni upgrade.")
            try:
                response = json.loads(body.decode("utf-8"))
                encoded = response["result"]["image"]
                image_bytes = base64.b64decode(encoded, validate=True)
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ImageProviderBlocked("Réponse image Cloudflare invalide.") from exc
            width, height = inspect_image(image_bytes, "image/jpeg")
            if (width, height) != (1024, 1024):
                raise ImageProviderBlocked("Résolution FLUX inattendue ; asset non accepté.")
            digest = hashlib.sha256(image_bytes).hexdigest()
            self.reservation_store.settle(
                evidence, reservation_id=reservation_id, neurons=neurons,
                output_sha256=digest, consumed=True,
            )
            return {
                "image_bytes": image_bytes, "media_type": "image/jpeg",
                "width_px": width, "height_px": height, "sha256": digest,
                "provider": PROVIDER_ID, "model_id": MODEL_ID,
                "estimated_neurons": neurons, "cost_minor": 0,
                "free_plan_only": True, "print_ready_300dpi": False,
                "quota_evidence_ref": evidence["evidence_ref"], "fallback_used": False,
            }
        except Exception:
            try:
                self.reservation_store.settle(
                    evidence, reservation_id=reservation_id, neurons=neurons,
                    output_sha256=None, consumed=sent,
                )
            except Exception:
                pass
            raise


def provider_from_environment(reservation_store: PostgresNeuronReservationStore) -> CloudflareFluxSchnellProvider:
    return CloudflareFluxSchnellProvider(
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        api_token=os.environ.get("CLOUDFLARE_API_TOKEN", ""),
        reservation_store=reservation_store,
    )
