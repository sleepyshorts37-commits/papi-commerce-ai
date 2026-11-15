import copy
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.kids_market_scoring import (
    CRITERIA, KidsMarketScoringError, build_market_report,
    score_assessment, validate_assessments,
)


def make_assessment():
    return {
        "book_id": "PKP-TEST01",
        "title": "Concept test",
        "criteria": {
            key: {"status": "pending", "score": None, "rationale": "", "evidence": []}
            for key in CRITERIA
        },
    }


def add_evidence(assessment, key, score=4):
    assessment["criteria"][key] = {
        "status": "assessed",
        "score": score,
        "rationale": "Évaluation de test documentée.",
        "evidence": [{
            "source_type": "official",
            "reference": "https://example.org/source",
            "observed_at": "2026-11-15",
            "claim": "Constat explicite de test.",
            "limitations": "Exemple de test, pas une donnée de marché réelle.",
        }],
    }


class KidsMarketScoringTests(unittest.TestCase):
    def test_empty_assessment_is_not_scored(self):
        result = score_assessment(make_assessment())
        self.assertEqual(result["status"], "not_assessed")
        self.assertIsNone(result["score"])
        self.assertEqual(result["decision"], "insufficient_evidence")
        self.assertEqual(len(result["pending_criteria"]), 8)

    def test_complete_evidence_calculates_weighted_score(self):
        item = make_assessment()
        for key in CRITERIA:
            add_evidence(item, key, 5)
        result = score_assessment(item)
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["decision"], "GO_TO_PROTOTYPE")

    def test_weighting_is_deterministic(self):
        item = make_assessment()
        for key in CRITERIA:
            add_evidence(item, key, 3)
        self.assertEqual(score_assessment(item)["score"], 60.0)

    def test_pending_criterion_prevents_ranking_score(self):
        item = make_assessment()
        for key in CRITERIA:
            add_evidence(item, key)
        item["criteria"]["jumia_unit_economics"] = {
            "status": "pending", "score": None, "rationale": "", "evidence": []
        }
        result = score_assessment(item)
        self.assertIsNone(result["score"])
        self.assertIn("jumia_unit_economics", result["pending_criteria"])

    def test_assessed_criterion_requires_evidence(self):
        item = make_assessment()
        item["criteria"]["demand_evidence"] = {
            "status": "assessed", "score": 4, "rationale": "Avis", "evidence": []
        }
        errors = validate_assessments({
            "schema_version": 1, "division_id": "papi_kids_publishing",
            "assessments": [item],
        })
        self.assertTrue(any("preuve" in error for error in errors))

    def test_score_outside_range_is_rejected(self):
        item = make_assessment()
        add_evidence(item, "demand_evidence", 6)
        with self.assertRaises(KidsMarketScoringError):
            score_assessment(item)

    def test_invalid_calendar_date_is_rejected(self):
        item = make_assessment()
        add_evidence(item, "demand_evidence")
        item["criteria"]["demand_evidence"]["evidence"][0]["observed_at"] = "2026-02-31"
        errors = validate_assessments({
            "schema_version": 1, "division_id": "papi_kids_publishing",
            "assessments": [item],
        })
        self.assertTrue(any("date observée invalide" in error for error in errors))

    def test_malformed_status_type_is_rejected_without_type_error(self):
        item = make_assessment()
        item["criteria"]["demand_evidence"]["status"] = []
        errors = validate_assessments({
            "schema_version": 1, "division_id": "papi_kids_publishing",
            "assessments": [item],
        })
        self.assertTrue(any("status doit être" in error for error in errors))

    def test_duplicate_ids_are_rejected(self):
        item = make_assessment()
        data = {"schema_version": 1, "division_id": "papi_kids_publishing",
                "assessments": [item, copy.deepcopy(item)]}
        self.assertTrue(any("dupliqué" in error for error in validate_assessments(data)))

    def test_report_keeps_five_concepts_unassessed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assessments.json"
            blank = make_assessment()
            data = {"schema_version": 1, "division_id": "papi_kids_publishing",
                    "assessments": [dict(blank, book_id=f"PKP-TEST0{i}") for i in range(1, 6)]}
            path.write_text(json.dumps(data), encoding="utf-8")
            report = build_market_report(path)
        self.assertEqual(report["total_concepts"], 5)
        self.assertEqual(report["not_assessed"], 5)
        self.assertEqual(report["ranking"], [])
        self.assertFalse(report["market_data_invented"])

    def test_duplicate_json_keys_are_rejected(self):
        from papi_core.kids_market_scoring import _unique_pairs
        with self.assertRaises(KidsMarketScoringError):
            _unique_pairs([("score", 1), ("score", 2)])


if __name__ == "__main__":
    unittest.main()
