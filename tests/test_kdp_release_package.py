import unittest
import zipfile
import io

from papi_core.kdp_release_package import (
    KDPReleaseGateError, build_kdp_candidate_package,
)


def args():
    return {
        "interior_pdf": b"%PDF-1.7\ninterior",
        "cover_pdf": b"%PDF-1.7\ncover",
        "metadata": {
            "title": "Nia et la rivière aux mille reflets",
            "language": "fr", "author": "Auteur confirmé",
            "trim_size": "official-template-selected",
            "price": "owner-approved", "territories": ["selected"],
        },
        "asset_reviews": [
            {"decision": "approved", "reviewer_id": "owner-reviewer",
             "content_sha256": f"{i:064x}"}
            for i in range(1, 25)
        ],
        "editorial_approval": {
            "approved": True, "reviewer_id": "independent-editor",
            "manuscript_sha256": "a" * 64,
        },
        "rights_evidence": {
            "commercial_use": True, "print_on_demand": True,
            "evidence_ref": "rights-contract-001",
        },
        "preflight_report": {
            "status": "ready_for_human_review", "kdp_upload_authorized": False,
        },
    }


class KDPReleasePackageTests(unittest.TestCase):
    def test_builds_candidate_zip_without_publishing(self):
        result = build_kdp_candidate_package(**args())
        self.assertEqual(result["status"], "candidate_ready_for_owner_review")
        self.assertFalse(result["kdp_upload_performed"])
        self.assertFalse(result["publication_authorized"])
        with zipfile.ZipFile(io.BytesIO(result["package_zip"])) as archive:
            self.assertEqual(set(archive.namelist()),
                             {"interior.pdf", "cover.pdf", "release-manifest.json"})

    def test_rejects_missing_human_illustration_approval(self):
        data = args()
        data["asset_reviews"].pop()
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)

    def test_rejects_missing_editorial_or_rights_approval(self):
        data = args()
        data["editorial_approval"]["approved"] = False
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)
        data = args()
        data["rights_evidence"]["print_on_demand"] = False
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)

    def test_rejects_failed_preflight_and_fake_pdf(self):
        data = args()
        data["preflight_report"]["status"] = "blocked"
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)
        data = args()
        data["interior_pdf"] = b"not pdf"
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)

    def test_requires_owner_metadata(self):
        data = args()
        data["metadata"]["author"] = ""
        with self.assertRaises(KDPReleaseGateError):
            build_kdp_candidate_package(**data)


if __name__ == "__main__":
    unittest.main()
