import unittest
from datetime import datetime, timezone

from papi_core.quality_gates import (
    LEVEL_REQUIREMENTS,
    QualityGateError,
    evaluate_quality_level,
    require_quality_level,
)


class QualityGateTests(unittest.TestCase):
    def evidence_for(self, levels=("prototype",)):
        keys = []
        for level, requirements in LEVEL_REQUIREMENTS.items():
            keys.extend(requirements)
            if level == levels[-1]:
                break
        now = datetime.now(timezone.utc).isoformat()
        return {
            key: {
                "status": "passed",
                "evidence_ref": f"ci://evidence/{key}",
                "verified_at": now,
                "reviewer": "quality-reviewer",
            }
            for key in keys
        }

    def test_no_evidence_cannot_claim_any_level(self):
        result = evaluate_quality_level({}, "prototype")
        self.assertIsNone(result["achieved_level"])
        self.assertFalse(result["requested_level_allowed"])
        self.assertFalse(result["publication_authorized"])

    def test_prototype_requires_all_five_evidence_records(self):
        evidence = self.evidence_for()
        self.assertEqual(evaluate_quality_level(evidence)["achieved_level"], "prototype")
        evidence.pop("responsive_smoke")
        result = evaluate_quality_level(evidence, "prototype")
        self.assertFalse(result["requested_level_allowed"])
        with self.assertRaises(QualityGateError):
            require_quality_level(evidence, "prototype")

    def test_mvp_is_cumulative(self):
        evidence = self.evidence_for(("mvp",))
        self.assertEqual(evaluate_quality_level(evidence)["achieved_level"], "mvp")
        evidence.pop("automated_tests")
        result = evaluate_quality_level(evidence, "mvp")
        self.assertFalse(result["requested_level_allowed"])
        self.assertIn("automated_tests", result["missing_for_requested_level"])

    def test_production_requires_independent_and_field_evidence(self):
        evidence = self.evidence_for(("professional_production",))
        self.assertEqual(
            evaluate_quality_level(evidence)["achieved_level"],
            "professional_production",
        )
        evidence["field_core_web_vitals"]["evidence_ref"] = ""
        self.assertFalse(
            evaluate_quality_level(evidence, "professional_production")["requested_level_allowed"]
        )

    def test_enterprise_critical_requires_all_additional_controls(self):
        evidence = self.evidence_for(("enterprise_critical",))
        self.assertEqual(
            evaluate_quality_level(evidence)["achieved_level"],
            "enterprise_critical",
        )
        evidence.pop("independent_penetration_test")
        self.assertFalse(
            evaluate_quality_level(evidence, "enterprise_critical")["requested_level_allowed"]
        )

    def test_failed_pending_or_unreviewed_evidence_is_rejected(self):
        evidence = self.evidence_for()
        evidence["html_safety"]["status"] = "pending"
        self.assertFalse(evaluate_quality_level(evidence, "prototype")["requested_level_allowed"])
        evidence["html_safety"]["status"] = "passed"
        evidence["html_safety"].pop("reviewer")
        self.assertFalse(evaluate_quality_level(evidence, "prototype")["requested_level_allowed"])

    def test_timezone_is_required_for_evidence_timestamp(self):
        evidence = self.evidence_for()
        evidence["automated_tests"]["verified_at"] = "2026-11-13T12:00:00"
        self.assertFalse(evaluate_quality_level(evidence, "prototype")["requested_level_allowed"])

    def test_unknown_level_and_non_object_evidence_are_rejected(self):
        with self.assertRaises(QualityGateError):
            evaluate_quality_level({}, "production")
        with self.assertRaises(QualityGateError):
            evaluate_quality_level([])


if __name__ == "__main__":
    unittest.main()
