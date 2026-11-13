import tempfile
import unittest
import zipfile
from pathlib import Path

from papi_core.website_builder import (
    WebsiteBuilderError,
    export_project,
    generate_project,
    quality_report,
    update_project,
)


class WebsiteBuilderTests(unittest.TestCase):
    def spec(self):
        return {
            "name": "Pharmacie Baobab",
            "tagline": "Votre santé, notre priorité",
            "description": "Présentation et informations de contact.",
            "contact": "Mbour — numéro à confirmer",
        }

    def test_generate_static_project_and_quality_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_project(tmp, "pharmacie-baobab", self.spec())
            self.assertFalse(result["published"])
            self.assertEqual(result["preview"], "static_file_only")
            report = quality_report(tmp, "pharmacie-baobab")
            self.assertTrue(report["passed"])
            self.assertTrue(all(report["checks"].values()))
            html = (Path(tmp) / "pharmacie-baobab" / "index.html").read_text()
            self.assertIn('<html lang="fr">', html)
            self.assertIn('name="viewport"', html)

    def test_professional_design_system_has_responsive_and_accessibility_basics(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_project(tmp, "studio", self.spec())
            css = (Path(tmp) / "studio" / "styles.css").read_text()
            self.assertIn("--accent:", css)
            self.assertIn("@media (max-width: 800px)", css)
            self.assertIn("@media (max-width: 520px)", css)
            self.assertIn(":focus-visible", css)
            self.assertIn("prefers-reduced-motion: reduce", css)

    def test_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            malicious = self.spec()
            malicious["name"] = '<script>alert("x")</script>'
            generate_project(tmp, "safe-site", malicious)
            html = (Path(tmp) / "safe-site" / "index.html").read_text()
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WebsiteBuilderError):
                generate_project(tmp, "../outside", self.spec())

    def test_unapproved_spec_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid = self.spec()
            invalid["shell_command"] = "rm -rf /"
            with self.assertRaises(WebsiteBuilderError):
                generate_project(tmp, "site", invalid)

    def test_duplicate_generation_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_project(tmp, "site", self.spec())
            with self.assertRaises(WebsiteBuilderError):
                generate_project(tmp, "site", self.spec())

    def test_iterative_update_changes_only_supported_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_project(tmp, "site", self.spec())
            result = update_project(tmp, "site", {"tagline": "Nouvelle accroche"})
            self.assertEqual(result["updated_fields"], ["tagline"])
            html = (Path(tmp) / "site" / "index.html").read_text()
            self.assertIn("Nouvelle accroche", html)
            with self.assertRaises(WebsiteBuilderError):
                update_project(tmp, "site", {"script": "alert(1)"})

    def test_export_contains_only_allowlisted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_project(tmp, "site", self.spec())
            project = Path(tmp) / "site"
            (project / "extra.txt").write_text("must not export")
            archive_path = Path(tmp) / "site.zip"
            export_project(tmp, "site", archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["site/index.html", "site/project.json", "site/styles.css"],
                )

    def test_export_rejects_destination_inside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_project(tmp, "site", self.spec())
            with self.assertRaises(WebsiteBuilderError):
                export_project(tmp, "site", Path(tmp) / "site" / "bundle.zip")


if __name__ == "__main__":
    unittest.main()
