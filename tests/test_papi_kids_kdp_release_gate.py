import unittest

from papi_core.papi_kids_kdp_release_gate import evaluate_kdp_release_gate


class KdpReleaseGateTests(unittest.TestCase):
    def make_status(self):
        upload_id = "PKP-UP-" + "a" * 32
        interior = "1" * 64
        cover = "2" * 64
        ebook = "3" * 64
        return {
            "upload_id": upload_id,
            "kdp_package_build": {
                "package_version": 2, "manifest_sha256": "4" * 64,
                "status": "generated_pending_manual_multiformat_review",
                "pdfs": {"interior": {"sha256": interior}, "cover": {"sha256": cover}},
                "ebook": {"sha256": ebook},
            },
            "kdp_package_reviews": {
                f"v2:{kind}": {
                    "approved": True, "decision": "approved", "package_version": 2,
                    "artifact_sha256": digest, "evidence_ref": "5" * 64,
                    "reviewer_id": "owner-01",
                }
                for kind, digest in (("interior", interior), ("cover", cover), ("ebook", ebook))
            },
            "content_safety_review": {"approved": True},
            "kdp_listing_metadata": {"commercial_use_confirmed": True},
            "kdp_listing_metadata_status": "ready_for_owner_review",
            "kdp_listing_metadata_blockers": [],
        }

    def test_all_hash_bound_reviews_and_rights_allow_final_owner_confirmation_only(self):
        result = evaluate_kdp_release_gate(self.make_status())
        self.assertTrue(result["eligible_for_final_owner_confirmation"])
        self.assertEqual(result["status"], "ready_for_final_owner_confirmation")
        self.assertFalse(result["kdp_upload_enabled"])
        self.assertFalse(result["publication_performed"])

    def test_missing_review_blocks(self):
        status = self.make_status()
        del status["kdp_package_reviews"]["v2:cover"]
        result = evaluate_kdp_release_gate(status)
        self.assertFalse(result["eligible_for_final_owner_confirmation"])
        self.assertTrue(any("cover" in item for item in result["blockers"]))

    def test_changed_artifact_hash_invalidates_old_review(self):
        status = self.make_status()
        status["kdp_package_build"]["pdfs"]["interior"]["sha256"] = "9" * 64
        result = evaluate_kdp_release_gate(status)
        self.assertTrue(any("interior" in item for item in result["blockers"]))

    def test_missing_child_safety_and_rights_block(self):
        status = self.make_status()
        status["content_safety_review"] = {"approved": False}
        status["kdp_listing_metadata"]["commercial_use_confirmed"] = False
        result = evaluate_kdp_release_gate(status)
        self.assertFalse(result["eligible_for_final_owner_confirmation"])
        self.assertGreaterEqual(len(result["blockers"]), 2)

    def test_missing_book_fails_closed(self):
        result = evaluate_kdp_release_gate(None)
        self.assertFalse(result["eligible_for_final_owner_confirmation"])
        self.assertFalse(result["kdp_upload_enabled"])


if __name__ == "__main__":
    unittest.main()
