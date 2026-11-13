"""Vérification Ed25519 avec registre et anti-rejeu Supabase partagés."""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .identity_ed25519 import Ed25519IdentityError, _canonical, _validate_agent


class SupabaseIdentityVerifier:
    """Vérifie une enveloppe Ed25519 avec tables/RPC Supabase côté serveur.

    Le store doit être un SupabaseStore configuré avec une clé serveur gardée
    dans l'environnement de confiance. Aucune clé privée n'est utilisée ici.
    """

    def __init__(self, store: Any, clock_skew_seconds: int = 300) -> None:
        if not callable(getattr(store, "_request", None)):
            raise ValueError("Un store Supabase compatible est obligatoire.")
        if not isinstance(clock_skew_seconds, int) or not 1 <= clock_skew_seconds <= 300:
            raise ValueError("Fenêtre temporelle invalide.")
        self.store = store
        self.clock_skew_seconds = clock_skew_seconds

    def verify(self, envelope: dict[str, Any], now: int | None = None) -> dict[str, Any]:
        required = {"agent_id", "key_version", "timestamp", "nonce", "payload", "signature"}
        if not isinstance(envelope, dict) or set(envelope) != required:
            raise Ed25519IdentityError("Enveloppe Ed25519 invalide.")
        agent_id, version = envelope["agent_id"], envelope["key_version"]
        _validate_agent(agent_id)
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise Ed25519IdentityError("Version de clé invalide.")
        timestamp = envelope["timestamp"]
        nonce = envelope["nonce"]
        signature_hex = envelope["signature"]
        current = int(time.time()) if now is None else int(now)
        if not isinstance(timestamp, int) or isinstance(timestamp, bool) or abs(current - timestamp) > self.clock_skew_seconds:
            raise Ed25519IdentityError("Signature expirée ou horloge désynchronisée.")
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
            raise Ed25519IdentityError("Nonce invalide.")
        try:
            signature = bytes.fromhex(signature_hex)
            if len(signature) != 64:
                raise ValueError("signature length")
        except (TypeError, ValueError) as exc:
            raise Ed25519IdentityError("Signature invalide.") from exc

        query = (
            "papi_agent_public_keys?agent_id=eq." + quote(agent_id, safe="")
            + "&key_version=eq." + str(version)
            + "&status=eq.active&select=public_key_hex"
        )
        rows = self.store._request("GET", query)
        if not isinstance(rows, list) or len(rows) != 1:
            raise Ed25519IdentityError("Clé publique absente, révoquée ou ambiguë.")
        try:
            public_bytes = bytes.fromhex(rows[0]["public_key_hex"])
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature, _canonical(agent_id, version, timestamp, nonce, envelope["payload"])
            )
        except (ValueError, KeyError, TypeError, InvalidSignature) as exc:
            raise Ed25519IdentityError("Signature Ed25519 incorrecte.") from exc

        consumed = self.store._request("POST", "rpc/papi_consume_agent_nonce", {
            "p_agent_id": agent_id,
            "p_key_version": version,
            "p_nonce": nonce,
            "p_expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp + self.clock_skew_seconds)),
        })
        if consumed is not True:
            raise Ed25519IdentityError("Rejeu détecté ou nonce non consommé.")
        return {"authenticated": True, "agent_id": agent_id,
                "key_version": version, "algorithm": "Ed25519",
                "replay_protected": True, "registry": "supabase"}
