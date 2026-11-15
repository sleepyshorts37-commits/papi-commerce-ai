import tempfile
import unittest
from pathlib import Path

from papi_core.papi_kids_asset_store import (
    IllustrationAssetError,
    inspect_image,
    store_illustration_asset,
)


def png(width=2550, height=2550):
    header = b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR"
    return header + width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"


class PapiKidsAssetStoreTests(unittest.TestCase):
    def test_inspects_png_dimensions(self):
        self.assertEqual(inspect_image(png(), "image/png"), (2550, 2550))

    def test_rejects_mismatched_or_unsupported_image(self):
        with self.assertRaises(IllustrationAssetError):
            inspect_image(png(), "image/jpeg")
        with self.assertRaises(IllustrationAssetError):
            inspect_image(b"not-an-image", "image/png")

    def test_stores_private_versioned_asset_and_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            (Path(root) / upload_id).mkdir(mode=0o700)
            asset = store_illustration_asset(
                root, upload_id=upload_id, page_number=1, version=1,
                image_bytes=png(), media_type="image/png",
                prompt_sha256="b" * 64,
            )
            target = Path(root) / upload_id / "illustrations" / "page-01-v001.png"
            self.assertTrue(target.exists())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(asset["width_px"], 2550)
            self.assertEqual(asset["review_status"], "pending_review")
            self.assertTrue(asset["human_approval_required"])

    def test_identical_version_is_idempotent_and_conflicting_version_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            (Path(root) / upload_id).mkdir(mode=0o700)
            first = store_illustration_asset(
                root, upload_id=upload_id, page_number=1, version=1,
                image_bytes=png(), media_type="image/png",
            )
            second = store_illustration_asset(
                root, upload_id=upload_id, page_number=1, version=1,
                image_bytes=png(), media_type="image/png",
            )
            self.assertEqual(first["sha256"], second["sha256"])
            with self.assertRaises(IllustrationAssetError):
                store_illustration_asset(
                    root, upload_id=upload_id, page_number=1, version=1,
                    image_bytes=png(3000, 3000), media_type="image/png",
                )

    def test_registration_failure_is_retryable_and_file_remains_private(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            (Path(root) / upload_id).mkdir(mode=0o700)
            first = store_illustration_asset(
                root, upload_id=upload_id, page_number=2, version=1,
                image_bytes=png(), media_type="image/png",
                asset_registrar=lambda metadata: (_ for _ in ()).throw(RuntimeError("db down")),
            )
            self.assertEqual(first["persistence_status"], "pending_retry")
            second = store_illustration_asset(
                root, upload_id=upload_id, page_number=2, version=1,
                image_bytes=png(), media_type="image/png",
                asset_registrar=lambda metadata: {"registered": True},
            )
            self.assertEqual(second["persistence_status"], "registered")


if __name__ == "__main__":
    unittest.main()
