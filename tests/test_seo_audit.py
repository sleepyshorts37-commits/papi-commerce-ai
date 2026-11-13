import tempfile
import unittest
from pathlib import Path

from papi_core.seo_audit import SEOAuditError, audit_static_site_seo


class StaticSEOAuditTests(unittest.TestCase):
    def create_site(self, root: Path) -> Path:
        site = root / "site"
        (site / "services").mkdir(parents=True)
        (site / "index.html").write_text(
            '<!doctype html><html lang="fr"><head>'
            '<title>Pharmacie du Centre | Santé et conseils</title>'
            '<meta name="description" content="Découvrez nos services de santé, nos conseils et notre accompagnement de proximité au quotidien.">'
            '<link rel="canonical" href="https://example.test/">'
            '<meta property="og:title" content="Pharmacie du Centre">'
            '<meta property="og:description" content="Votre santé au quotidien.">'
            '</head><body><h1>Bienvenue à la pharmacie</h1>'
            '<a href="/services/">Nos services</a></body></html>',
            encoding="utf-8",
        )
        (site / "services/index.html").write_text(
            '<html lang="fr"><head><title>Nos services de santé et pharmacie</title>'
            '<meta name="description" content="Consultez les services et conseils proposés par notre équipe de pharmacie pour votre santé.">'
            '<meta property="og:title" content="Nos services">'
            '<meta property="og:description" content="Les services de notre pharmacie.">'
            '</head><body><h1>Nos services</h1><a href="../index.html">Accueil</a></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        (site / "robots.txt").write_text("User-agent: *\\nAllow: /\\n", encoding="utf-8")
        return site

    def test_valid_site_passes_without_network_or_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_site(Path(tmp))
            report = audit_static_site_seo(tmp, "site")
            self.assertTrue(report["passed"], report["errors"])
            self.assertEqual(report["page_count"], 2)
            self.assertEqual(report["sitemap"], "valid_xml")
            self.assertEqual(report["network_requests"], 0)
            self.assertFalse(report["published"])

    def test_missing_metadata_and_multiple_h1_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = self.create_site(Path(tmp))
            (site / "index.html").write_text(
                '<html><head><title>Accueil</title></head>'
                '<body><h1>Premier</h1><h1>Deuxième</h1></body></html>',
                encoding="utf-8",
            )
            report = audit_static_site_seo(tmp, "site")
            self.assertFalse(report["passed"])
            self.assertTrue(any("description absente" in item for item in report["errors"]))
            self.assertTrue(any("exactement un H1" in item for item in report["errors"]))
            self.assertTrue(any("lang absent" in item for item in report["errors"]))

    def test_broken_internal_link_and_javascript_link_are_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = self.create_site(Path(tmp))
            page = site / "index.html"
            page.write_text(
                page.read_text(encoding="utf-8").replace(
                    'href="/services/"', 'href="/missing/"'
                ).replace("</body>", '<a href="javascript:alert(1)">X</a></body>'),
                encoding="utf-8",
            )
            report = audit_static_site_seo(tmp, "site")
            self.assertFalse(report["passed"])
            self.assertTrue(any("sans cible" in item for item in report["errors"]))
            self.assertTrue(any("javascript:" in item for item in report["errors"]))

    def test_missing_social_and_canonical_metadata_are_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = self.create_site(Path(tmp))
            page = site / "services/index.html"
            page.write_text(
                page.read_text(encoding="utf-8").replace(
                    '<meta property="og:title" content="Nos services">',
                    "",
                ).replace(
                    '<meta property="og:description" content="Les services de notre pharmacie.">',
                    "",
                ),
                encoding="utf-8",
            )
            report = audit_static_site_seo(tmp, "site")
            self.assertTrue(report["passed"], report["errors"])
            self.assertTrue(any("Open Graph" in item for item in report["warnings"]))
            self.assertTrue(any("canonical" in item for item in report["warnings"]))

    def test_rejects_invalid_slug_and_missing_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SEOAuditError):
                audit_static_site_seo(tmp, "../outside")
            with self.assertRaises(SEOAuditError):
                audit_static_site_seo(tmp, "missing")

    def test_rejects_symlinked_html_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = self.create_site(Path(tmp))
            target = site / "index.html"
            target.unlink()
            external = Path(tmp) / "outside.html"
            external.write_text("<html></html>", encoding="utf-8")
            target.symlink_to(external)
            with self.assertRaises(SEOAuditError):
                audit_static_site_seo(tmp, "site")


if __name__ == "__main__":
    unittest.main()
