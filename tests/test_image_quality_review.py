import unittest

from papi_core.image_quality_review import (
    ImageQualityError, REQUIRED_CHECKS, review_generated_image,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"valid-test-image"


def passing_reviewer(**kwargs):
    return {"checks": {
        name: {"score": 0.95, "passed": True, "findings": []}
        for name in REQUIRED_CHECKS
    }}


class ImageQualityReviewTests(unittest.TestCase):
    def test_missing_reviewer_fails_closed(self):
        result = review_generated_image(
            image_bytes=PNG, declared_content_type="image/png",
            prompt="A child reading", reviewer=None,
        )
        self.assertEqual(result["status"], "awaiting_visual_review")
        self.assertFalse(result["human_approved"])

    def test_valid_semantic_review_still_requires_human_approval(self):
        result = review_generated_image(
            image_bytes=PNG, declared_content_type="image/png",
            prompt="A child reading", reviewer=passing_reviewer,
        )
        self.assertEqual(result["status"], "pending_human_approval")
        self.assertEqual(result["overall_score"], 0.95)
        self.assertFalse(result["human_approved"])

    def test_low_safety_score_blocks_image(self):
        def reviewer(**kwargs):
            checks = passing_reviewer()["checks"]
            checks["safety"] = {"score": 0.2, "passed": False, "findings": ["unsafe"]}
            return {"checks": checks}
        result = review_generated_image(
            image_bytes=PNG, declared_content_type="image/png",
            prompt="A child reading", reviewer=reviewer,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("safety", result["blocking_reasons"])

    def test_invalid_signature_is_blocked_before_reviewer(self):
        called = []
        result = review_generated_image(
            image_bytes=b"not-an-image", declared_content_type="image/png",
            prompt="A child reading", reviewer=lambda **kw: called.append(True),
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(called, [])

    def test_mime_mismatch_and_oversize_are_blocked(self):
        result = review_generated_image(
            image_bytes=PNG, declared_content_type="image/jpeg",
            prompt="A child reading", reviewer=passing_reviewer, max_bytes=5,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("mime_matches", result["blocking_reasons"])
        self.assertIn("size_within_limit", result["blocking_reasons"])

    def test_malformed_reviewer_output_is_rejected(self):
        with self.assertRaises(ImageQualityError):
            review_generated_image(
                image_bytes=PNG, declared_content_type="image/png",
                prompt="A child reading", reviewer=lambda **kw: {"checks": {}},
            )


if __name__ == "__main__":
    unittest.main()
