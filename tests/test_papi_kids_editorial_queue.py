import json
import tempfile
import unittest
from pathlib import Path

from papi_core.papi_kids_editorial_queue import analyze_queued_manuscript, get_queue_record


class PapiKidsEditorialQueueTests(unittest.TestCase):
    def test_offline_analysis_is_deterministic_and_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ("PKP-UP-" + "a" * 32)
            folder.mkdir(mode=0o700)
            (folder / "manuscript.md").write_text("# Mon livre\n\n## Première scène\nTexte.\n", encoding="utf-8")
            (folder / "metadata.json").write_text(json.dumps({"status": "queued_for_analysis"}), encoding="utf-8")
            job = {"upload_id": folder.name, "status": "queued_for_analysis", "stored_filename": "manuscript.md"}
            (folder / "job.json").write_text(json.dumps(job), encoding="utf-8")
            result = analyze_queued_manuscript(root, folder.name)
            self.assertEqual(result["status"], "analysis_ready")
            self.assertEqual(result["analysis"]["section_count"], 2)
            self.assertFalse(result["analysis"]["ai_invoked"])
            self.assertFalse(result["analysis"]["provider_invoked"])
            again = analyze_queued_manuscript(root, folder.name)
            self.assertEqual(again, result)
            metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "analysis_ready")

    def test_plain_text_without_headings_requires_editor_review(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ("PKP-UP-" + "b" * 32)
            folder.mkdir()
            (folder / "manuscript.txt").write_text("Un récit sans titres.", encoding="utf-8")
            (folder / "metadata.json").write_text(json.dumps({"status": "queued_for_analysis"}), encoding="utf-8")
            (folder / "job.json").write_text(json.dumps({
                "upload_id": folder.name, "status": "queued_for_analysis", "stored_filename": "manuscript.txt"
            }), encoding="utf-8")
            result = analyze_queued_manuscript(root, folder.name)
            self.assertEqual(result["status"], "needs_editor_review")

    def test_structured_child_story_runs_offline_safety_screening(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ("PKP-UP-" + "c" * 32)
            folder.mkdir(mode=0o700)
            pages = [
                f"### Page {n} — Scène {n}\n" +
                ("Nia entre dans la rivière." if n == 1 else "Nia observe la rivière depuis le chemin avec Awa.")
                for n in range(1, 25)
            ]
            (folder / "manuscript.md").write_text("\n\n".join(pages), encoding="utf-8")
            (folder / "metadata.json").write_text(json.dumps({"status": "queued_for_analysis"}), encoding="utf-8")
            (folder / "job.json").write_text(json.dumps({
                "upload_id": folder.name, "status": "queued_for_analysis", "stored_filename": "manuscript.md"
            }), encoding="utf-8")
            result = analyze_queued_manuscript(root, folder.name)
        self.assertEqual(result["status"], "needs_editor_review")
        screening = result["analysis"]["child_safety_screening"]
        self.assertGreater(screening["critical_issue_count"], 0)
        self.assertFalse(screening["automatic_approval"])
        self.assertFalse(result["analysis"]["ai_invoked"])

    def test_safe_structured_story_has_no_flags_but_still_requires_human_review(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ("PKP-UP-" + "d" * 32)
            folder.mkdir(mode=0o700)
            pages = [
                f"### Page {n} — Scène {n}\nNia observe la rivière depuis le chemin avec Awa, une adulte."
                for n in range(1, 25)
            ]
            (folder / "manuscript.md").write_text("\n\n".join(pages), encoding="utf-8")
            (folder / "metadata.json").write_text(json.dumps({"status": "queued_for_analysis"}), encoding="utf-8")
            (folder / "job.json").write_text(json.dumps({
                "upload_id": folder.name, "status": "queued_for_analysis", "stored_filename": "manuscript.md"
            }), encoding="utf-8")
            result = analyze_queued_manuscript(root, folder.name)
        self.assertEqual(result["status"], "analysis_ready")
        self.assertEqual(result["analysis"]["child_safety_screening"]["issue_count"], 0)
        self.assertTrue(result["analysis"]["child_safety_screening"]["human_review_required"])

    def test_invalid_upload_id_is_rejected(self):
        with self.assertRaises(ValueError):
            get_queue_record("/tmp", "../escape")


if __name__ == "__main__":
    unittest.main()
