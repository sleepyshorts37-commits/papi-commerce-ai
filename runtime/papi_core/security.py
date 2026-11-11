"""Contrôles de sécurité locaux en lecture seule, en mode fail-closed."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
POLICY_FILE=ROOT/"config"/"policy.json"
REQUIRED_DISABLED=("execution_enabled","external_actions_enabled")

class SecurityError(ValueError):
    """Politique ou posture de sécurité non conforme."""

def validate_policy(policy: Any) -> list[str]:
    errors=[]
    if not isinstance(policy,dict): return ["La politique doit être un objet JSON."]
    if policy.get("project")!="PAPI COMMERCE AI": errors.append("Projet de politique invalide.")
    for key in REQUIRED_DISABLED:
        if policy.get(key) is not False: errors.append(f"{key} doit rester false.")
    if policy.get("default_budget_xof")!=0: errors.append("Le budget par défaut doit rester à 0 XOF.")
    if policy.get("agent_execution_status")!="not_deployed": errors.append("Le statut des agents doit rester not_deployed tant que le déploiement n'est pas vérifié.")
    permissions=policy.get("action_permissions")
    for action in ("external_communication","financial","legal"):
        config=permissions.get(action) if isinstance(permissions,dict) else None
        if not isinstance(config,dict) or config.get("enabled") is not False or config.get("owner_approval") is not True:
            errors.append(f"La permission {action} doit rester désactivée et soumise au propriétaire.")
    forbidden=policy.get("never_allowed")
    if not isinstance(forbidden,list) or not {"store_credentials_in_repository","request_otp_or_pin_in_chat","impersonate_people","spam_or_evade_platform_limits","fabricate_revenue_or_sales","bypass_kyc_or_access_controls"}.issubset(set(forbidden)):
        errors.append("Les interdictions fondamentales sont incomplètes.")
    return errors

def security_report(policy_path: Path=POLICY_FILE, root: Path=ROOT) -> dict[str,Any]:
    try: policy=json.loads(Path(policy_path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise SecurityError("Politique de sécurité illisible.") from exc
    errors=validate_policy(policy)
    gitignore=Path(root)/".gitignore"
    try: ignore_text=gitignore.read_text(encoding="utf-8")
    except OSError: ignore_text=""
    if ".env" not in ignore_text: errors.append(".gitignore doit exclure les fichiers .env.")
    if not any(line.strip()=="!.env.example" for line in ignore_text.splitlines()):
        errors.append(".gitignore doit autoriser uniquement le modèle .env.example.")
    return {"mode":"read_only_local","status":"blocked" if errors else "safe_scaffold",
            "execution_enabled":policy.get("execution_enabled") is True,
            "external_actions_enabled":policy.get("external_actions_enabled") is True,
            "default_budget_xof":policy.get("default_budget_xof"),
            "errors":errors,"no_network_access":True,"secrets_printed":False}

def check_security(policy_path: Path=POLICY_FILE, root: Path=ROOT) -> dict[str,Any]:
    report=security_report(policy_path,root)
    if report["errors"]: raise SecurityError("; ".join(report["errors"]))
    return report
