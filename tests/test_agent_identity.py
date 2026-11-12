from datetime import datetime, timezone

from papi_core.agent_identity import validate_identity, validate_identity_registry


def _card(**updates):
    value = {
        "identity_id": "PAPI-AGENT-0001",
        "agent_id": "astou",
        "full_name": "Astou",
        "role": "Coordination",
        "department": "Direction",
        "manager_id": "owner",
        "mission": "Coordonner les activités autorisées.",
        "competencies": ["coordination"],
        "objectives": ["produire un rapport"],
        "autonomy_level": "bounded",
        "permissions": ["read_reports"],
        "prohibited_actions": ["spend_money"],
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "assignment_history": [],
        "evaluation_history": [],
        "profile_state": "complete",
    }
    value.update(updates)
    return value


def test_valid_identity_card_is_accepted():
    assert validate_identity(_card(), {"astou": {"id": "astou"}}) == []


def test_unknown_agent_is_rejected():
    errors = validate_identity(_card(), {})
    assert any("agent_id" in error for error in errors)


def test_incomplete_card_cannot_be_active():
    errors = validate_identity(
        _card(profile_state="incomplete", manager_id=None), {"astou": {"id": "astou"}}
    )
    assert any("incomplète" in error for error in errors)
    assert any("responsable" in error for error in errors)


def test_naive_timestamp_is_rejected():
    errors = validate_identity(
        _card(created_at="2026-11-12T10:00:00"), {"astou": {"id": "astou"}}
    )
    assert any("fuseau" in error for error in errors)


def test_duplicate_identity_and_agent_are_rejected():
    card = _card()
    errors = validate_identity_registry(
        {"schema_version": 1, "identities": [card, card]},
        {"astou": {"id": "astou"}},
    )
    assert any("Identifiant numérique dupliqué" in error for error in errors)
    assert any("Une seule carte" in error for error in errors)


def test_registry_requires_supported_schema_version():
    try:
        validate_identity_registry({"schema_version": 2, "identities": []}, {})
    except ValueError as exc:
        assert "schema_version 1" in str(exc)
    else:
        raise AssertionError("Invalid schema version was accepted")
