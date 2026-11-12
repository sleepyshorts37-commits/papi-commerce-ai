"""Contrôle des identités du registre central PAPI."""
import json
from pathlib import Path

from papi_core.agent_name_registry import audit_legacy_name_collisions, validate_agent_name_registry

ROOT = Path(__file__).resolve().parents[1]
registry = json.loads((ROOT / "data/agents/registry.json").read_text(encoding="utf-8"))
legacy_doc = json.loads((ROOT / "data/agents.json").read_text(encoding="utf-8"))
identity_doc = json.loads((ROOT / "data/agent-identities.json").read_text(encoding="utf-8"))

# Fusionner les deux sources par identifiant afin qu'une même personne ne soit
# comptée qu'une fois, tout en réservant les noms et alias déjà documentés.
legacy_by_id = {}
for item in legacy_doc.get("agents", []):
    key = item.get("id") or item.get("agent_id")
    if key:
        legacy_by_id[key] = dict(item)
for item in identity_doc.get("identities", []):
    key = item.get("agent_id")
    if key:
        current = legacy_by_id.setdefault(key, {"id": key})
        current["full_name"] = item.get("full_name") or current.get("full_name")
        current["aliases"] = list(dict.fromkeys(
            (current.get("aliases") or []) + (item.get("aliases") or [])
        ))
legacy_agents = list(legacy_by_id.values())

errors = validate_agent_name_registry(registry, legacy_agents)
if errors:
    raise SystemExit("\n".join(errors))

conflicts = audit_legacy_name_collisions(legacy_agents)
print(f"OK — {len(registry['agents'])} postes contrôlés ; aucune nouvelle identité ne réutilise un nom historique.")
if conflicts:
    print("AVERTISSEMENT — collisions historiques à résoudre avant attribution/activation :")
    for item in conflicts:
        print(f"- {item['type']}: {item['normalized_name']} ({', '.join(item['agent_ids'])})")
else:
    print("OK — aucune collision historique détectée.")
