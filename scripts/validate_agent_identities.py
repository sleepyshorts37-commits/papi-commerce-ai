"""Valide les 40 cartes d'identité documentaires PAPI."""
import json
from pathlib import Path

from papi_core.agent_identity import validate_identity_registry

ROOT = Path(__file__).resolve().parents[1]
agents_doc = json.loads((ROOT / "data/agents.json").read_text(encoding="utf-8"))
identity_doc = json.loads((ROOT / "data/agent-identities.json").read_text(encoding="utf-8"))
agents = {agent["id"]: agent for agent in agents_doc["agents"]}
errors = validate_identity_registry(identity_doc, agents)

expected_ids = set(agents)
cards = identity_doc.get("identities", [])
actual_ids = {card.get("agent_id") for card in cards if isinstance(card, dict)}
if len(cards) != len(agents):
    errors.append(f"Nombre de cartes incorrect : {len(cards)} au lieu de {len(agents)}.")
if actual_ids != expected_ids:
    errors.append("Les cartes ne correspondent pas exactement aux agents du registre.")

if errors:
    raise SystemExit("\n".join(errors))

print(f"OK — {len(cards)} cartes d'identité valides et reliées aux agents.")
