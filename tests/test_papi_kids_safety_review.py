import hashlib
import unittest
from pathlib import Path

from papi_core.papi_kids_safety_review import (
    PapiKidsSafetyReviewError,
    analyze_child_safety,
    attest_child_safety_review,
)


def manuscript(page_one):
    pages = [page_one] + [f"Page sans alerte numéro {n}." for n in range(2, 25)]
    return "\n\n".join(
        f"### Page {n} — Scène {n}\n{text}"
        for n, text in enumerate(pages, start=1)
    )


class PapiKidsSafetyReviewTests(unittest.TestCase):
    def test_flags_child_water_contact_and_hazard_handling(self):
        source = manuscript("Nia entre dans la rivière et ramasse une seringue près de la berge.")
        result = analyze_child_safety(source)
        self.assertGreaterEqual(result["critical_issue_count"], 2)
        self.assertFalse(result["automatic_approval"])
        self.assertEqual(result["status"], "needs_human_safety_review")

    def test_flags_unsupervised_danger_and_requires_resolution_notes(self):
        source = manuscript("Nia reste seule près de la rivière.")
        result = analyze_child_safety(source)
        self.assertGreater(result["high_issue_count"], 0)
        with self.assertRaises(PapiKidsSafetyReviewError):
            attest_child_safety_review(
                result, decision="approved", reviewer_id="owner-01",
                reviewed_at="2026-11-15", evidence_ref="review-01",
            )
        attestation = attest_child_safety_review(
            result, decision="approved", reviewer_id="owner-01",
            reviewed_at="2026-11-15", evidence_ref="review-01",
            resolution_notes="Le passage a été réécrit et revu avec un adulte responsable.",
        )
        self.assertTrue(attestation["approved"])
        self.assertEqual(attestation["manuscript_sha256"], result["manuscript_sha256"])

    def test_french_negative_safety_instructions_are_not_flagged(self):
        source = manuscript(
            "Nia regarde le sol humide qui descend vers l'eau. "
            "Les enfants ne descendent pas dans l'eau et ne ramassent jamais les déchets. "
            "Nous ne buvons pas cette eau."
        )
        result = analyze_child_safety(source)
        self.assertEqual(result["issue_count"], 0)

    def test_active_child_actions_still_flagged_with_subject_and_conjugations(self):
        source = manuscript("Nia entre dans la rivière et Bako ramasse une seringue.")
        result = analyze_child_safety(source)
        rules = {issue["rule_id"] for issue in result["pages"][0]["issues"]}
        self.assertIn("child_in_water", rules)
        self.assertIn("child_handles_hazard", rules)

    def test_safe_story_still_requires_human_approval(self):
        source = manuscript("Nia observe la rivière depuis le chemin avec Awa, une adulte.")
        result = analyze_child_safety(source)
        self.assertEqual(result["issue_count"], 0)
        self.assertFalse(result["automatic_approval"])
        attestation = attest_child_safety_review(
            result, decision="approved", reviewer_id="editor-01",
            reviewed_at="2026-11-15", evidence_ref="safety-review-02",
        )
        self.assertTrue(attestation["approved"])

    def test_attestation_is_bound_to_exact_source_hash(self):
        first = analyze_child_safety(manuscript("Nia observe la rivière depuis le chemin."))
        second = analyze_child_safety(manuscript("Nia observe la rivière depuis un chemin sûr."))
        attestation = attest_child_safety_review(
            first, decision="approved", reviewer_id="editor-01",
            reviewed_at="2026-11-15", evidence_ref="safety-03",
        )
        self.assertNotEqual(attestation["manuscript_sha256"], second["manuscript_sha256"])

    def test_pkp0001_v2_working_manuscript_has_no_lexical_flags_but_is_not_auto_approved(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "publishing" / "papi-kids" / "PKP-0001" / "manuscript-v2.md").read_text(encoding="utf-8")
        result = analyze_child_safety(source)
        self.assertEqual(result["page_count"], 24)
        self.assertEqual(result["issue_count"], 0)
        self.assertFalse(result["automatic_approval"])
        self.assertTrue(result["human_review_required"])

    def test_requires_24_ordered_pages(self):
        with self.assertRaises(PapiKidsSafetyReviewError):
            analyze_child_safety("### Page 1 — Unique\nUne seule page.", expected_pages=24)


if __name__ == "__main__":
    unittest.main()
