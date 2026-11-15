"""Evidence-gated, deterministic market scoring for PAPI KIDS concepts.

Scores are supplied by a reviewer and must be backed by traceable evidence.
Missing criteria never become zeroes and never produce a portfolio ranking.
This module is local-only: it does not browse, contact people, or publish.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CRITERIA = {
    "demand_evidence": 20,
    "competition_position": 10,
    "differentiation": 15,
    "kdp_unit_economics": 15,
    "jumia_unit_economics": 10,
    "editorial_feasibility": 10,
    "rights_and_child_safety": 10,
    "source_reliability": 10,
}
SCORE_MIN = 0
SCORE_MAX = 5
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://[^\s]+$")
SOURCE_TYPES = {"official", "marketplace", "publisher", "interview_adult", "cost_quote", "internal_review", "other"}
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "data" / "divisions" / "papi-kids-market-assessments.json"


class KidsMarketScoringError(ValueError):
    """Invalid or incomplete evidence-based market assessment."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise KidsMarketScoringError(f"Clé JSON dupliquée : {key}")
        result[key] = value
    return result


def load_assessments(path: Path = DEFAULT_FILE) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            raise KidsMarketScoringError("Fichier symbolique ou trop volumineux.")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except KidsMarketScoringError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KidsMarketScoringError("Fichier d'évaluations absent ou JSON invalide.") from exc
    errors = validate_assessments(data)
    if errors:
        raise KidsMarketScoringError("; ".join(errors))
    return data


def validate_assessments(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != {"schema_version", "division_id", "assessments"}:
        return ["Le document doit contenir schema_version, division_id et assessments."]
    if data["schema_version"] != 1 or data["division_id"] != "papi_kids_publishing":
        errors.append("Version ou division invalide.")
    assessments = data["assessments"]
    if not isinstance(assessments, list):
        return errors + ["assessments doit être une liste."]
    seen: set[str] = set()
    for index, item in enumerate(assessments):
        prefix = f"Évaluation #{index + 1}"
        if not isinstance(item, dict) or set(item) != {"book_id", "title", "criteria"}:
            errors.append(f"{prefix}: champs attendus book_id, title, criteria.")
            continue
        book_id, title, criteria = item["book_id"], item["title"], item["criteria"]
        if not isinstance(book_id, str) or not re.fullmatch(r"PKP-[A-Z0-9]{4,20}", book_id):
            errors.append(f"{prefix}: book_id invalide.")
        elif book_id in seen:
            errors.append(f"{prefix}: book_id dupliqué.")
        else:
            seen.add(book_id)
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            errors.append(f"{prefix}: titre invalide.")
        if not isinstance(criteria, dict) or set(criteria) != set(CRITERIA):
            errors.append(f"{prefix}: les huit critères doivent être présents exactement.")
            continue
        for key, entry in criteria.items():
            label = f"{prefix}/{key}"
            if not isinstance(entry, dict) or set(entry) != {"status", "score", "rationale", "evidence"}:
                errors.append(f"{label}: structure invalide.")
                continue
            status, score = entry["status"], entry["score"]
            if status not in {"pending", "assessed"}:
                errors.append(f"{label}: status doit être pending ou assessed.")
            if status == "pending":
                if score is not None or entry["evidence"] != []:
                    errors.append(f"{label}: un critère pending doit avoir score null et evidence vide.")
            else:
                if isinstance(score, bool) or not isinstance(score, int) or not SCORE_MIN <= score <= SCORE_MAX:
                    errors.append(f"{label}: score entier attendu entre 0 et 5.")
                if not isinstance(entry["rationale"], str) or not entry["rationale"].strip():
                    errors.append(f"{label}: justification obligatoire.")
                evidence = entry["evidence"]
                if not isinstance(evidence, list) or not evidence:
                    errors.append(f"{label}: au moins une preuve est obligatoire.")
                else:
                    for proof in evidence:
                        if not isinstance(proof, dict) or set(proof) != {"source_type", "reference", "observed_at", "claim", "limitations"}:
                            errors.append(f"{label}: format de preuve invalide.")
                            continue
                        if proof["source_type"] not in SOURCE_TYPES:
                            errors.append(f"{label}: source_type inconnu.")
                        if not isinstance(proof["reference"], str) or not proof["reference"].strip():
                            errors.append(f"{label}: référence de source obligatoire.")
                        if not isinstance(proof["observed_at"], str) or not DATE_RE.fullmatch(proof["observed_at"]):
                            errors.append(f"{label}: date observée attendue au format AAAA-MM-JJ.")
                        if not isinstance(proof["claim"], str) or not proof["claim"].strip():
                            errors.append(f"{label}: constat de preuve obligatoire.")
                        if not isinstance(proof["limitations"], str):
                            errors.append(f"{label}: limites de la preuve obligatoires, chaîne vide autorisée.")
    return errors


def score_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    """Calculate a weighted score only when every criterion has evidence."""
    errors = validate_assessments({
        "schema_version": 1,
        "division_id": "papi_kids_publishing",
        "assessments": [assessment],
    })
    if errors:
        raise KidsMarketScoringError("; ".join(errors))
    pending = [key for key, entry in assessment["criteria"].items() if entry["status"] != "assessed"]
    if pending:
        return {
            "book_id": assessment["book_id"],
            "title": assessment["title"],
            "status": "not_assessed",
            "score": None,
            "decision": "insufficient_evidence",
            "pending_criteria": pending,
            "weights": CRITERIA,
            "market_data_invented": False,
        }
    weighted = sum(assessment["criteria"][key]["score"] * weight for key, weight in CRITERIA.items())
    total_weight = sum(CRITERIA.values())
    score = round(weighted / total_weight * 20, 2)
    decision = "GO_TO_PROTOTYPE" if score >= 70 else "REWORK" if score >= 50 else "STOP"
    return {
        "book_id": assessment["book_id"],
        "title": assessment["title"],
        "status": "assessed",
        "score": score,
        "decision": decision,
        "pending_criteria": [],
        "weights": CRITERIA,
        "market_data_invented": False,
        "note": "Score consultatif fondé sur des notes humaines et leurs preuves ; GO autorise uniquement l'étape prototype après validation humaine.",
    }


def build_market_report(path: Path = DEFAULT_FILE) -> dict[str, Any]:
    data = load_assessments(path)
    results = [score_assessment(item) for item in data["assessments"]]
    ranked = sorted(
        (item for item in results if item["status"] == "assessed"),
        key=lambda item: (-item["score"], item["book_id"]),
    )
    return {
        "division_id": data["division_id"],
        "total_concepts": len(results),
        "assessed": sum(item["status"] == "assessed" for item in results),
        "not_assessed": sum(item["status"] == "not_assessed" for item in results),
        "ranking": ranked,
        "assessments": results,
        "market_data_invented": False,
        "external_actions_performed": False,
    }
