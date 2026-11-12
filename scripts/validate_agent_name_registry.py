"""Contrôle des identités du registre central PAPI."""
import json
from pathlib import Path

from papi_core.agent_name_registry import audit_legacy_name_collisions, validate_agent_name_registry

ROOT = Path(__file__).resolve().parents[1]
registry = json.loads((ROOT / "data/agents/registry.json").read_text(encoding="utf-8"))
legacy_doc = json.loads((ROOT / "data/agents.json").read_text(encoding="utf-8"))
legacy_agents = legacy_doc.get("agents", [])

errors = validate_agent_name_registry(registry, legacy_agents)
if errors:
    raise SystemExit("\\n".join(errors))

conflicts = audit_legacy_name_collisions(legacy_agents)
print(f"OK — {len(registry['agents'])} postes contrôlés ; aucune nouvelle identité ne réutilise un nom historique.")
if conflicts:
    print("AVERTISSEMENT — collisions historiques à résoudre avant attribution/activation :")
    for item in conflicts:
        print(f"- {item['type']}: {item['normalized_name']} ({', '.join(item['agent_ids'])})")
else:
    print("OK — aucune collision historique détectée.")
