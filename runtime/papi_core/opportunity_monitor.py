"""Read-only lifecycle monitoring for supplied opportunity snapshots."""
from datetime import date

DECISIONS = {"test", "investigate", "hold", "reject"}
STATUSES = {"active", "paused", "closed", "won", "lost"}
MAX_RECORDS = 500


def _date(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _index(records, field):
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError(f"{field} must be a list of at most {MAX_RECORDS}")
    result = {}
    allowed = {"opportunity_id", "title", "observed_at", "score", "decision", "status",
               "verified_payment_xof", "payment_reference", "payment_verified_by"}
    required = {"opportunity_id", "title", "observed_at", "score", "decision", "status"}
    for item in records:
        if not isinstance(item, dict) or set(item) - allowed or not required.issubset(item):
            raise ValueError("Invalid snapshot fields")
        oid, title = item["opportunity_id"], item["title"]
        if not isinstance(oid, str) or not oid.strip() or len(oid) > 120:
            raise ValueError("Invalid opportunity_id")
        if oid in result:
            raise ValueError("Duplicate opportunity_id")
        if not isinstance(title, str) or not title.strip() or len(title) > 500:
            raise ValueError("Invalid title")
        _date(item["observed_at"], "observed_at")
        score = item["score"]
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("score must be an integer from 0 to 100")
        if item["decision"] not in DECISIONS or item["status"] not in STATUSES:
            raise ValueError("Invalid decision or status")
        result[oid] = dict(item)
    return result


def monitor_opportunities(previous, current, *, as_of, stale_after_days=14):
    """Compare snapshots; absence is never interpreted as closure."""
    today = _date(as_of, "as_of")
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int) or not 1 <= stale_after_days <= 365:
        raise ValueError("stale_after_days must be from 1 to 365")
    old, new = _index(previous, "previous"), _index(current, "current")
    changes, stale, disappeared, payments = [], [], [], []
    for oid, item in new.items():
        age = (today - _date(item["observed_at"], "observed_at")).days
        if age < 0:
            raise ValueError("Observation date cannot be in the future")
        prior = old.get(oid)
        if prior is None:
            change = "new"
        elif item["score"] > prior["score"]:
            change = "improved"
        elif item["score"] < prior["score"]:
            change = "declined"
        elif item["decision"] != prior["decision"] or item["status"] != prior["status"]:
            change = "status_changed"
        else:
            change = "unchanged"
        changes.append({"opportunity_id": oid, "title": item["title"], "change": change,
                        "previous_score": prior["score"] if prior else None,
                        "current_score": item["score"], "age_days": age})
        if age >= stale_after_days and item["status"] not in {"closed", "won", "lost"}:
            stale.append({"opportunity_id": oid, "title": item["title"], "age_days": age,
                          "reason": "Human revalidation required"})
        amount = item.get("verified_payment_xof", 0)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("verified_payment_xof must be a non-negative integer")
        if amount:
            ref, verifier = item.get("payment_reference"), item.get("payment_verified_by")
            if not isinstance(ref, str) or not ref.strip() or not isinstance(verifier, str) or not verifier.strip():
                raise ValueError("Payment requires a reference and verifier")
            payments.append({"opportunity_id": oid, "amount_xof": amount,
                             "payment_reference": ref, "verified_by": verifier})
    for oid, item in old.items():
        if oid not in new:
            disappeared.append({"opportunity_id": oid, "title": item["title"],
                                 "meaning": "absent_from_current_snapshot_not_proof_of_closure"})
    return {
        "status": "completed_read_only", "as_of": as_of,
        "summary": {"previous_count": len(old), "current_count": len(new),
                    "new": sum(x["change"] == "new" for x in changes),
                    "improved": sum(x["change"] == "improved" for x in changes),
                    "declined": sum(x["change"] == "declined" for x in changes),
                    "stale": len(stale), "disappeared_not_closed": len(disappeared),
                    "verified_revenue_xof": sum(x["amount_xof"] for x in payments)},
        "changes": changes, "stale_opportunities": stale,
        "disappeared_opportunities": disappeared, "verified_payments": payments,
        "controls": {"network_accessed": False, "external_actions_enabled": False,
                     "financial_actions_enabled": False, "budget_xof": 0,
                     "execution_authorized": False},
        "limitations": ["Snapshots are supplied by an operator or external system.",
                        "Missing from a snapshot does not prove closure.",
                        "Declared payment references require independent checking through an authorized source.",
                        "No search, contact, spending or transaction is performed."]
    }
