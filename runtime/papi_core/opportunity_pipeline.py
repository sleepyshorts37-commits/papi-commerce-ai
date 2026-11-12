"""End-to-end read-only opportunity intake, verification and triage pipeline."""
from __future__ import annotations

from typing import Any

from runtime.papi_core.opportunity_scanner import normalize_search_results, evaluate_opportunities

MAX_BATCH_SIZE = 200


def run_opportunity_pipeline(records: list[dict[str, Any]], *, collected_at: str) -> dict[str, Any]:
    """Normalize supplied public-search hits, evaluate attestations and prepare human triage.

    This function never performs network access, contact, publication, spending or transactions.
    A candidate decision of 'test' means eligible for human review, not permission to execute.
    """
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    if len(records) > MAX_BATCH_SIZE:
        raise ValueError(f"Un lot ne peut pas dépasser {MAX_BATCH_SIZE} résultats.")

    scan = normalize_search_results(records, collected_at=collected_at)

    # IDs must be unique within a batch so reports and later manual follow-up remain unambiguous.
    seen_ids: set[str] = set()
    unique_items = []
    duplicate_ids = []
    for item in scan["items"]:
        opportunity_id = item["opportunity_id"]
        if opportunity_id in seen_ids:
            duplicate_ids.append({
                "opportunity_id": opportunity_id,
                "title": item["title"],
                "reason": "Identifiant d'opportunité dupliqué dans le même lot."
            })
            continue
        seen_ids.add(opportunity_id)
        unique_items.append(item)

    scan["items"] = unique_items
    scan["items_normalized"] = len(unique_items)
    scan["duplicate_ids"] = duplicate_ids

    evaluation = evaluate_opportunities(scan)
    manual_review = [
        {
            "opportunity_id": item["opportunity_id"],
            "title": item["title"],
            "score": item["score"],
            "proposed_decision": item["decision"],
            "next_step": "human_review_only"
        }
        for item in evaluation["top_three"]
    ]

    return {
        "status": "completed_read_only",
        "collected_at": collected_at,
        "summary": {
            "received": len(records),
            "normalized": len(unique_items),
            "duplicates_skipped": scan["duplicates_skipped"],
            "duplicate_ids_rejected": len(duplicate_ids),
            "invalid_inputs_rejected": scan["items_rejected"],
            "verified_attestations": evaluation["verified_count"],
            "awaiting_verification": evaluation["uncertain_count"],
            "rejected": evaluation["rejected_count"] + len(duplicate_ids),
            "manual_review_candidates": len(manual_review)
        },
        "manual_review_queue": manual_review,
        "evaluation": evaluation,
        "controls": {
            "network_accessed": False,
            "external_actions_enabled": False,
            "financial_actions_enabled": False,
            "budget_xof": 0,
            "execution_authorized": False,
            "human_approval_required_before_any_test": True
        },
        "limitations": [
            "Les résultats de recherche sont fournis par une source externe ou un opérateur humain.",
            "Les attestations ne sont pas authentifiées indépendamment par ce pipeline.",
            "Une décision 'test' est une recommandation de revue humaine, jamais une autorisation d'exécution.",
            "Aucun résultat ne constitue une vente ou un revenu ; seuls les paiements réellement vérifiés peuvent être comptabilisés."
        ]
    }
