"""Read-only normalizer and qualification pipeline for supplied public-search results."""
from __future__ import annotations
from datetime import date
from typing import Any
from urllib.parse import urlparse
from runtime.papi_core.opportunity_scoring import rank_opportunities

MAX_ITEMS = 200
CHECKS = {"senegal_access", "payment_and_withdrawal", "fees", "terms", "legal_compliance"}
VERIFICATION_FIELDS = CHECKS | {"reviewer", "reviewed_at", "evidence_urls"}


def _text(value: Any, field: str, required: bool = True) -> str:
    if not isinstance(value, str) or len(value) > 1000 or (required and not value.strip()):
        raise ValueError(f"{field} invalide.")
    return value.strip()


def _https(value: Any, field: str) -> str:
    value = _text(value, field)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field} doit être une URL HTTPS publique.")
    return value


def normalize_search_results(records: list[dict[str, Any]], *, collected_at: str) -> dict[str, Any]:
    """Normalize hits supplied by an authorized search provider or human; never browses."""
    if not isinstance(records, list) or len(records) > MAX_ITEMS:
        raise ValueError(f"records doit contenir au maximum {MAX_ITEMS} résultats.")
    _text(collected_at, "collected_at")
    items, rejected, seen = [], [], set()
    for index, raw in enumerate(records):
        try:
            if not isinstance(raw, dict) or set(raw) - {
                "title", "url", "snippet", "published_at", "source_name",
                "opportunity_id", "verification", "scoring"
            }:
                raise ValueError("Objet invalide ou champs inconnus.")
            title, url = _text(raw.get("title"), "title"), _https(raw.get("url"), "url")
            key = url.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "opportunity_id": _text(raw.get("opportunity_id", f"OPP-SCAN-{index + 1:04d}"), "opportunity_id"),
                "title": title, "source_url": url,
                "source_name": _text(raw.get("source_name", urlparse(url).netloc), "source_name"),
                "snippet": _text(raw.get("snippet", ""), "snippet", False),
                "published_at": _text(raw.get("published_at", ""), "published_at", False),
                "collected_at": collected_at, "verification_status": "needs_verification",
                "verification": raw.get("verification"), "scoring": raw.get("scoring")
            })
        except (TypeError, ValueError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    return {
        "status": "normalized", "items_received": len(records), "items_normalized": len(items),
        "duplicates_skipped": len(records) - len(items) - len(rejected),
        "items_rejected": len(rejected), "items": items, "rejections": rejected,
        "network_accessed": False, "execution_authorized": False
    }


def _attestation(item: dict[str, Any]) -> tuple[bool, str]:
    v = item.get("verification")
    if not isinstance(v, dict) or set(v) != VERIFICATION_FIELDS:
        return False, "Fiche de vérification absente ou incomplète."
    if any(v.get(key) != "confirmed" for key in CHECKS):
        return False, "Accès Sénégal, paiement/retrait, frais, conditions ou conformité non confirmés."
    if not isinstance(v.get("reviewer"), str) or not v["reviewer"].strip():
        return False, "Vérificateur non identifié."
    try:
        date.fromisoformat(_text(v.get("reviewed_at"), "reviewed_at")[:10])
        urls = v.get("evidence_urls")
        if not isinstance(urls, list) or not urls:
            raise ValueError("Aucune preuve publique.")
        for url in urls:
            _https(url, "evidence_url")
    except (TypeError, ValueError) as exc:
        return False, str(exc)
    if not isinstance(item.get("scoring"), dict):
        return False, "Données de notation manquantes."
    return True, ""


def evaluate_opportunities(scan: dict[str, Any]) -> dict[str, Any]:
    """Only fully attested records reach the scoring engine."""
    if not isinstance(scan, dict) or not isinstance(scan.get("items"), list):
        raise ValueError("Résultat de scan invalide.")
    verified, uncertain, rejected = [], [], list(scan.get("rejections", []))
    for item in scan["items"]:
        if not isinstance(item, dict):
            rejected.append({"reason": "Fiche candidate invalide."})
            continue
        ok, reason = _attestation(item)
        if not ok:
            item["verification_status"] = "needs_verification"
            uncertain.append({"opportunity_id": item.get("opportunity_id"),
                              "title": item.get("title"), "reason": reason})
            continue
        score = dict(item["scoring"])
        score.update({
            "opportunity_id": item["opportunity_id"], "title": item["title"],
            "source": item["source_url"], "source_checked_at": item["verification"]["reviewed_at"],
            "country_access": "confirmed", "payment_access": "confirmed",
            "legal_status": "compliant", "evidence_level": "verified"
        })
        verified.append(score)
        item["verification_status"] = "verified_attested"
    ranking = rank_opportunities(verified)
    rejected.extend(ranking["rejections"])
    return {
        "status": "evaluated", "discovered_count": len(scan["items"]),
        "verified_count": len(verified), "uncertain_count": len(uncertain),
        "rejected_count": len(rejected), "discovered": scan["items"],
        "verified": verified, "uncertain": uncertain, "rejected": rejected,
        "top_three": ranking["top_three"], "read_only": True,
        "network_accessed": False, "execution_authorized": False,
        "limitations": [
            "Les résultats sont fournis par une source externe ou un humain ; ce module ne navigue pas sur Internet.",
            "verified_attested est une attestation structurée : le code ne visite pas les liens et n'authentifie pas les preuves.",
            "Aucune inscription, prise de contact, publication, dépense ou transaction n'est exécutée."
        ]
    }


def scan_opportunity_signals(signals: list[dict[str, Any]], *, as_of: str) -> dict[str, Any]:
    """Compatibilité du tableau de bord : normalise des signaux fournis, sans réseau."""
    if not isinstance(signals, list) or len(signals) > MAX_ITEMS:
        raise ValueError(f"signals doit contenir au maximum {MAX_ITEMS} éléments.")
    _text(as_of, "as_of")
    normalized, rejected = [], 0
    required = ("signal_id", "source", "source_ref", "business_line", "market", "customer_segment", "offer")
    for signal in signals:
        if not isinstance(signal, dict) or any(not isinstance(signal.get(k), str) or not signal[k].strip() for k in required):
            rejected += 1
            continue
        normalized.append({**signal, "triage_status": "needs_business_review"})
    return {"status": "normalized" if normalized else "empty", "signals_received": len(signals),
            "signals_rejected": rejected, "signals": normalized, "network_accessed": False,
            "execution_authorized": False}
