"""Real Chromium smoke tests for the isolated local website preview."""
import os
import tempfile
import threading
import unittest
from pathlib import Path

from playwright.async_api import async_playwright

from papi_core.multi_page_builder import generate_multi_page_project
from papi_core.preview_server import create_preview_server


class PreviewBrowserSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        workspace = Path(self.workspace.name)
        architecture = {
            "project_name": "Demo PAPI",
            "requirements": [
                {"id": "brand", "description": "Présenter la marque", "priority": "must"},
                {"id": "contact", "description": "Afficher le contact", "priority": "must"},
            ],
            "pages": [
                {"slug": "home", "title": "Accueil", "purpose": "Découvrir le service", "requirements": ["brand"]},
                {"slug": "contact", "title": "Contact", "purpose": "Contacter l'équipe", "requirements": ["contact"]},
            ],
        }
        generate_multi_page_project(
            workspace,
            "demo-papi",
            {"name": "Demo PAPI", "industry": "corporate", "tagline": "Démonstration locale"},
            architecture,
        )
        self.server = create_preview_server(workspace / "demo-papi")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.workspace.cleanup()

    async def test_home_page_renders_in_real_chromium(self):
        page = await self.browser.new_page()
        response = await page.goto(self.base_url + "/", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)
        self.assertIn("Demo PAPI", await page.title())
        self.assertEqual(await page.locator("h1").count(), 1)
        self.assertTrue(await page.locator("main#main-content").is_visible())
        self.assertGreater(await page.locator("body").evaluate("(el) => el.scrollHeight"), 0)
        await page.close()

    async def test_secondary_route_and_shared_stylesheet_load(self):
        page = await self.browser.new_page()
        failed_local_requests = []
        external_requests = []
        page.on(
            "request",
            lambda request: external_requests.append(request.url)
            if not request.url.startswith(self.base_url) else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_local_requests.append(request.url)
            if request.url.startswith(self.base_url) else None,
        )
        response = await page.goto(self.base_url + "/contact/", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)
        self.assertIn("Contact", await page.locator("h1").inner_text())
        stylesheet = await page.locator('link[rel="stylesheet"]').get_attribute("href")
        self.assertEqual(stylesheet, "../styles.css")
        self.assertEqual(failed_local_requests, [])
        self.assertEqual(external_requests, [])
        await page.close()


    async def test_responsive_viewports_navigation_and_screenshots(self):
        page = await self.browser.new_page()
        artifact_dir = Path(os.environ.get('PAPI_BROWSER_ARTIFACT_DIR', 'artifacts/browser'))
        artifact_dir.mkdir(parents=True, exist_ok=True)
        viewports = [('mobile', 390, 844), ('tablet', 768, 1024), ('desktop', 1440, 900)]
        for label, width, height in viewports:
            await page.set_viewport_size({'width': width, 'height': height})
            response = await page.goto(self.base_url + '/', wait_until='networkidle')
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200)
            self.assertTrue(await page.locator('h1').is_visible(), label)
            self.assertTrue(await page.locator('main#main-content').is_visible(), label)
            dimensions = await page.evaluate('() => ({viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth})')
            self.assertLessEqual(dimensions['content'], dimensions['viewport'] + 1, f'Horizontal overflow at {label}: {dimensions}')
            contact_link = page.locator('a[href*="contact"]').first
            self.assertTrue(await contact_link.is_visible(), f'Contact navigation missing at {label}')
            await page.screenshot(path=str(artifact_dir / f'preview-{label}.png'), full_page=True)
            await contact_link.click()
            self.assertTrue(page.url.rstrip('/').endswith('/contact/index.html'), page.url)
            self.assertTrue(await page.locator('h1').is_visible())
        await page.close()

if __name__ == "__main__":
    unittest.main()
