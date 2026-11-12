import json
from pathlib import Path
from unittest.mock import patch

import pytest

from papi_core.agent_identity_auth import (
    AgentIdentityAuthenticationError,
    authenticate_agent_request,
)


def _write(path: Path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _fixtures(tmp_path, *, status="planned", profile_state="incomplete"):
    agent = {
        "id": "astou", "name": "Astou", "status": "active",
        "permissions": ["chat.send"], "prohibited": ["spend_money"],
    }
    card = {
        "identity_id": "PAPI-ID-ASTOU", "agent_id": "astou",
        "full_name": "Astou", "role": "Coordination", "department": "Direction",
        "manager_id": "owner", "mission": "Coordonner les opérations autorisées.",
        "competencies": ["coordination"], "objectives": ["rapports fiables"],
        "autonomy_level": "bounded", "permissions": ["chat.send"],
        "prohibited_actions": ["spend_money"], "status": status,
        "created_at": "2026-11-12T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": profile_state,
    }
    identities = {"schema_version": 1, "identities": [card]}
    agents = {"agents": [agent]}
    return (
        _write(tmp_path / "identities.json", identities),
        _write(tmp_path / "agents.json", agents),
    )


def test_planned_identity_cannot_authenticate(tmp_path):
    identities, agents = _fixtures(tmp_path)
    with pytest.raises(AgentIdentityAuthenticationError, match="non activée"):
        authenticate_agent_request(
            {"agent_id": "astou"}, identities_path=identities, agents_path=agents,
            public_registry_path=tmp_path / "keys.json", replay_db=tmp_path / "replay.db",
        )


def test_permission_drift_fails_closed(tmp_path):
    identities, agents = _fixtures(tmp_path, status="active", profile_state="complete")
    data = json.loads(identities.read_text())
    data["identities"][0]["permissions"] = ["chat.send", "chat.broadcast"]
    _write(identities, data)
    with pytest.raises(AgentIdentityAuthenticationError, match="permissions"):
        authenticate_agent_request(
            {"agent_id": "astou"}, identities_path=identities, agents_path=agents,
            public_registry_path=tmp_path / "keys.json", replay_db=tmp_path / "replay.db",
        )


def test_active_identity_is_bound_to_ed25519_verification(tmp_path):
    identities, agents = _fixtures(tmp_path, status="active", profile_state="complete")
    envelope = {"agent_id": "astou"}
    expected = {"authenticated": True, "agent_id": "astou", "key_version": 1}
    with patch("papi_core.agent_identity_auth.verify_ed25519_request", return_value=expected) as verify:
        result = authenticate_agent_request(
            envelope, identities_path=identities, agents_path=agents,
            public_registry_path=tmp_path / "keys.json", replay_db=tmp_path / "replay.db",
        )
    verify.assert_called_once()
    assert result["identity_id"] == "PAPI-ID-ASTOU"
    assert result["identity_verified"] is True
