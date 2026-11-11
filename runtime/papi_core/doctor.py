"""Diagnostic local de configuration PAPI, sans connexion réseau ni affichage de secrets."""
from __future__ import annotations

import os
from urllib.parse import urlparse


def diagnose_environment(environ: dict[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ
    url = env.get("SUPABASE_URL", "").strip()
    key = env.get("SUPABASE_KEY", "").strip()
    parsed = urlparse(url) if url else None

    url_ok = bool(parsed and parsed.scheme == "https" and parsed.hostname and
                  parsed.hostname.endswith(".supabase.co"))
    key_ok = bool(key)
    policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "policy.json"))
    try:
        import json
        with open(policy_path, encoding="utf-8") as stream:
            policy = json.load(stream)
        execution_enabled = policy.get("execution_enabled") is True
        external_actions_enabled = policy.get("external_actions_enabled") is True
    except (OSError, ValueError):
        execution_enabled = None
        external_actions_enabled = None

    checks = {
        "supabase_url_configured": url_ok,
        "supabase_key_configured": key_ok,
        "policy_execution_enabled": execution_enabled,
        "policy_external_actions_enabled": external_actions_enabled,
    }
    ready = url_ok and key_ok
    return {
        "status": "configuration_present" if ready else "configuration_incomplete",
        "network_test_performed": False,
        "checks": checks,
        "secrets_displayed": False,
        "worker_start_allowed": False,
        "message": (
            "Configuration présente ; cela ne valide ni la clé ni les droits Supabase."
            if ready else
            "Configuration incomplète. Définir les variables dans l'environnement serveur protégé."
        ),
    }
