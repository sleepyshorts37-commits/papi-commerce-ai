"""Contrôle global des noms d'usage des agents PAPI."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any


def normalize_name(value: str) -> str:
    """Normalise casse, accents, ponctuation et séparateurs."""
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value)


def _tokens(value: str) -> list[str]:
    if not isinstance(value, str):
        return []
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", normalized)


def _records(source: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = source.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Le champ '{key}' doit être une liste.")
    if any(not isinstance(item, dict) for item in value):
        raise ValueError(f"Chaque élément de '{key}' doit être un objet.")
    return value


def audit_legacy_name_collisions(legacy_agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Signale les collisions déjà présentes dans les registres historiques."""
    given: dict[str, list[str]] = defaultdict(list)
    full: dict[str, list[str]] = defaultdict(list)
    for agent in legacy_agents:
        agent_id = str(agent.get("id") or agent.get("agent_id") or "unknown")
        name = agent.get("name") or agent.get("full_name") or ""
        if not isinstance(name, str) or not name.strip():
            continue
        first = _tokens(name)
        if first:
            given[first[0]].append(agent_id)
        normalized = normalize_name(name)
        if normalized:
            full[normalized].append(agent_id)
        for alias in agent.get("aliases", []) if isinstance(agent.get("aliases", []), list) else []:
            alias_tokens = _tokens(alias)
            if alias_tokens:
                given[alias_tokens[0]].append(agent_id)
            alias_key = normalize_name(alias)
            if alias_key:
                full[alias_key].append(agent_id)
    conflicts = []
    for key, ids in given.items():
        unique_ids = sorted(set(ids))
        if len(unique_ids) > 1:
            conflicts.append({"type": "given_name", "normalized_name": key, "agent_ids": unique_ids})
    for key, ids in full.items():
        unique_ids = sorted(set(ids))
        if len(unique_ids) > 1:
            conflicts.append({"type": "full_name_or_alias", "normalized_name": key, "agent_ids": unique_ids})
    return sorted(conflicts, key=lambda item: (item["type"], item["normalized_name"]))


def validate_agent_name_registry(
    registry: dict[str, Any],
    legacy_agents: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Valide IDs et noms attribués, en réservant les noms historiques."""
    if not isinstance(registry, dict) or registry.get("schema_version") != "1.0.0":
        raise ValueError("Registre invalide : schema_version '1.0.0' requis.")
    agents = _records(registry, "agents")
    errors: list[str] = []
    ids: set[str] = set()
    reserved_given: dict[str, str] = {}
    reserved_full: dict[str, str] = {}

    for legacy in legacy_agents or []:
        if not isinstance(legacy, dict):
            continue
        legacy_id = str(legacy.get("id") or legacy.get("agent_id") or "legacy")
        legacy_name = legacy.get("name") or legacy.get("full_name") or ""
        if isinstance(legacy_name, str) and legacy_name.strip():
            parts = _tokens(legacy_name)
            if parts:
                reserved_given.setdefault(parts[0], legacy_id)
            key = normalize_name(legacy_name)
            if key:
                reserved_full.setdefault(key, legacy_id)
        aliases = legacy.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if not isinstance(alias, str):
                    continue
                parts = _tokens(alias)
                if parts:
                    reserved_given.setdefault(parts[0], legacy_id)
                key = normalize_name(alias)
                if key:
                    reserved_full.setdefault(key, legacy_id)

    seen_given: dict[str, str] = {}
    seen_full: dict[str, str] = {}
    for index, agent in enumerate(agents, 1):
        agent_id = agent.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            errors.append(f"Agent #{index}: agent_id manquant.")
            continue
        if agent_id in ids:
            errors.append(f"Identifiant agent dupliqué : {agent_id}.")
        ids.add(agent_id)

        given_name = agent.get("given_name")
        full_name = agent.get("full_name")
        aliases = agent.get("aliases", [])
        if aliases is None:
            aliases = []
        if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
            errors.append(f"{agent_id}: aliases doit être une liste de chaînes non vides.")
            aliases = []

        if given_name is None and full_name is None:
            if agent.get("lifecycle_status") not in {"planned", "suspended", "retired"}:
                errors.append(f"{agent_id}: nom obligatoire avant toute activation.")
            continue
        if not isinstance(given_name, str) or not given_name.strip():
            errors.append(f"{agent_id}: given_name obligatoire lorsqu'une identité est attribuée.")
            continue
        if not isinstance(full_name, str) or not full_name.strip():
            errors.append(f"{agent_id}: full_name obligatoire lorsqu'une identité est attribuée.")
            continue

        given_key = normalize_name(given_name)
        full_key = normalize_name(full_name)
        full_tokens = _tokens(full_name)
        if not given_key or not full_key or not full_tokens:
            errors.append(f"{agent_id}: nom invalide après normalisation.")
            continue
        if given_key != normalize_name(full_tokens[0]):
            errors.append(f"{agent_id}: given_name doit correspondre au premier prénom du full_name.")
        if given_key in reserved_given:
            errors.append(f"{agent_id}: prénom déjà réservé par l'agent historique {reserved_given[given_key]}.")
        if given_key in seen_given:
            errors.append(f"{agent_id}: prénom dupliqué avec {seen_given[given_key]}.")
        seen_given[given_key] = agent_id
        if full_key in reserved_full:
            errors.append(f"{agent_id}: nom complet déjà réservé par l'agent historique {reserved_full[full_key]}.")
        if full_key in seen_full:
            errors.append(f"{agent_id}: nom complet dupliqué avec {seen_full[full_key]}.")
        seen_full[full_key] = agent_id

        for alias in aliases:
            alias_key = normalize_name(alias)
            alias_tokens = _tokens(alias)
            if not alias_key or not alias_tokens:
                errors.append(f"{agent_id}: alias invalide.")
                continue
            if alias_tokens[0] in reserved_given or alias_tokens[0] in seen_given:
                owner = reserved_given.get(alias_tokens[0]) or seen_given.get(alias_tokens[0])
                if owner != agent_id:
                    errors.append(f"{agent_id}: alias/prénom en collision avec {owner}.")
            if alias_key in reserved_full or alias_key in seen_full:
                owner = reserved_full.get(alias_key) or seen_full.get(alias_key)
                if owner != agent_id:
                    errors.append(f"{agent_id}: alias/nom complet en collision avec {owner}.")
            seen_given.setdefault(alias_tokens[0], agent_id)
            seen_full.setdefault(alias_key, agent_id)

    return errors
