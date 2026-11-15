import hashlib
import tempfile
import unittest
from pathlib import Path

from papi_core.image_asset_center import AssetCenterError, LocalImageAssetCenter


PNG = b"\x89PNG\r\n\x1a\n" + b"test-payload"


class AssetCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.center = LocalImageAssetCenter(Path(self.temp.name) / "library")
        self.args = dict(
            book_id="book-001", page_id="page-01", page_number=1,
            idempotency_key="papi-image:abc123", model="@cf/test/image",
            image_bytes=PNG, content_type="image/png",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_persists_and_verifies_content_integrity(self):
        record = self.center.put(**self.args)
        self.assertEqual(record["status"], "pending_visual_review")
        self.assertFalse(record["human_approved"])
        self.assertEqual(record["content_sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(self.center.read_bytes(record), PNG)

    def test_identical_replay_is_idempotent(self):
        first = self.center.put(**self.args)
        second = self.center.put(**self.args)
        self.assertEqual(first, second)
        self.assertEqual(len(self.center.list_assets(book_id="book-001")), 1)

    def test_same_key_different_bytes_is_rejected(self):
        self.center.put(**self.args)
        with self.assertRaises(AssetCenterError):
            self.center.put(**{**self.args, "image_bytes": PNG + b"different"})

    def test_rejects_mime_mismatch_and_unknown_format(self):
        with self.assertRaises(AssetCenterError):
            self.center.put(**{**self.args, "content_type": "image/jpeg"})
        with self.assertRaises(AssetCenterError):
            self.center.put(**{**self.args, "image_bytes": b"not-an-image", "content_type": None})

    def test_rejects_path_traversal_and_oversized_asset(self):
        with self.assertRaises(AssetCenterError):
            self.center.put(**{**self.args, "book_id": "../escape"})
        limited = LocalImageAssetCenter(Path(self.temp.name) / "small", max_asset_bytes=8)
        with self.assertRaises(AssetCenterError):
            limited.put(**self.args)

    def test_review_requires_human_identity_and_evidence(self):
        self.center.put(**self.args)
        with self.assertRaises(AssetCenterError):
            self.center.review(
                book_id="book-001", page_id="page-01",
                idempotency_key="papi-image:abc123", decision="approved",
                reviewer_id="reviewer-1", evidence="ok",
            )
        approved = self.center.review(
            book_id="book-001", page_id="page-01",
            idempotency_key="papi-image:abc123", decision="approved",
            reviewer_id="reviewer-1",
            evidence="Personnages cohérents, composition validée, aucun défaut visible.",
        )
        self.assertTrue(approved["human_approved"])
        self.assertEqual(approved["status"], "approved")

    def test_pending_assets_can_be_resumed_without_provider_call(self):
        self.center.put(**self.args)
        pending = self.center.list_assets(book_id="book-001", status="pending_visual_review")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["idempotency_key"], self.args["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
