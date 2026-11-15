import hashlib
import tempfile
import unittest
from pathlib import Path

from papi_core.image_quality_audit import ImageQualityAuditError, ImageQualityAuditLog


class ImageQualityAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.log = ImageQualityAuditLog(Path(self.temp.name) / "audit")
        self.digest = hashlib.sha256(b"image-bytes").hexdigest()
        self.report = {
            "status": "pending_human_approval",
            "content_sha256": self.digest,
            "human_approved": False,
            "approval_required": True,
            "blocking_reasons": [],
        }
        self.args = dict(
            event_id="event-001", book_id="book-001", page_id="page-01",
            content_sha256=self.digest, report=self.report,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_append_and_list_preserve_unapproved_state(self):
        event = self.log.append(**self.args)
        self.assertFalse(event["human_approval_granted"])
        self.assertFalse(event["report"]["human_approved"])
        self.assertEqual(self.log.list_events(book_id="book-001", page_id="page-01"), [event])

    def test_identical_replay_is_idempotent(self):
        first = self.log.append(**self.args)
        second = self.log.append(**self.args)
        self.assertEqual(first, second)
        self.assertEqual(len(self.log.list_events(book_id="book-001")), 1)

    def test_event_id_cannot_be_reused_for_different_content(self):
        self.log.append(**self.args)
        changed = {**self.report, "blocking_reasons": ["safety"]}
        with self.assertRaises(ImageQualityAuditError):
            self.log.append(**{**self.args, "report": changed})

    def test_report_must_match_image_and_remain_unapproved(self):
        with self.assertRaises(ImageQualityAuditError):
            self.log.append(**{**self.args, "content_sha256": "0" * 64})
        with self.assertRaises(ImageQualityAuditError):
            self.log.append(**{
                **self.args,
                "report": {**self.report, "human_approved": True},
            })

    def test_identifiers_and_status_are_validated(self):
        with self.assertRaises(ImageQualityAuditError):
            self.log.append(**{**self.args, "event_id": "../escape"})
        with self.assertRaises(ImageQualityAuditError):
            self.log.append(**{
                **self.args,
                "report": {**self.report, "status": "approved"},
            })

    def test_events_are_separate_and_append_only(self):
        first = self.log.append(**self.args)
        second = self.log.append(**{**self.args, "event_id": "event-002"})
        self.assertNotEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(self.log.list_events(book_id="book-001")), 2)
        self.assertEqual(len(list((Path(self.temp.name) / "audit" / "events").glob("*.json"))), 2)


if __name__ == "__main__":
    unittest.main()
