import tempfile
import unittest
from pathlib import Path

from papi_core.kids_project import KidsProjectError, create_project


class KidsProjectGeneratorTests(unittest.TestCase):
    def test_creates_six_editable_working_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            result = create_project(
                "PKP-TEST01", "Les aventures de Nia", output_root=Path(directory)
            )
            project = Path(result["project_path"])
            self.assertEqual(result["file_count"], 6)
            self.assertEqual(len(result["created_files"]), 6)
            self.assertTrue((project / "brief.md").is_file())
            self.assertTrue((project / "manuscript.md").is_file())
            self.assertTrue((project / "metadata.json").is_file())
            self.assertTrue((project / "production-checklist.md").is_file())
            self.assertTrue((project / "quality-report.json").is_file())
            self.assertFalse(result["catalog_updated"])
            self.assertFalse(result["external_actions_performed"])

    def test_existing_project_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "PKP-TEST01"
            project.mkdir()
            sentinel = project / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(KidsProjectError):
                create_project("PKP-TEST01", "Titre", output_root=Path(directory))
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_invalid_book_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KidsProjectError):
                create_project("../BAD", "Titre", output_root=Path(directory))

    def test_invalid_age_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KidsProjectError):
                create_project("PKP-TEST01", "Titre", age_min=9, age_max=4, output_root=Path(directory))

    def test_unhashable_product_type_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KidsProjectError):
                create_project("PKP-TEST01", "Titre", product_type=[], output_root=Path(directory))

    def test_symlink_output_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(KidsProjectError):
                create_project("PKP-TEST01", "Titre", output_root=link)
            self.assertEqual(list(real.iterdir()), [])

    def test_project_pack_has_no_approval_or_publication_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            result = create_project("PKP-TEST01", "Titre", output_root=Path(directory))
            project = Path(result["project_path"])
            metadata = (project / "metadata.json").read_text(encoding="utf-8")
            quality = (project / "quality-report.json").read_text(encoding="utf-8")
            self.assertIn('"publication_status": "not_submitted"', metadata)
            self.assertIn('"human_approval_required": true', metadata)
            self.assertIn('"review_status": "pending"', quality)
            self.assertIn('"reviewer": null', quality)


if __name__ == "__main__":
    unittest.main()
