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



    async def test_sector_accent_text_meets_wcag_aa_contrast(self):
        page = await self.browser.new_page()
        response = await page.goto(self.base_url + "/", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)
        contrast = await page.evaluate("""() => {
            const element = document.querySelector('.feature-index');
            const foreground = getComputedStyle(element).color;
            const background = getComputedStyle(element.parentElement).backgroundColor;
            const rgb = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number);
            const luminance = (value) => {
                const channels = rgb(value).map((part) => {
                    const c = part / 255;
                    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
                });
                return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
            };
            const first = luminance(foreground);
            const second = luminance(background);
            return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
        }""")
        self.assertGreaterEqual(contrast, 4.5, f"Accent text contrast below WCAG AA: {contrast:.2f}:1")
        await page.close()



    async def test_semantic_structure_and_navigation_on_every_generated_route(self):
        page = await self.browser.new_page()
        routes = [("/", "Accueil"), ("/contact/", "Contact")]
        for route, expected_label in routes:
            response = await page.goto(self.base_url + route, wait_until="networkidle")
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200, route)
            audit = await page.evaluate("""() => {
                const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
                const levels = headings.map((heading) => Number(heading.tagName.slice(1)));
                const links = [...document.querySelectorAll('a')];
                const navs = [...document.querySelectorAll('nav')];
                const current = [...document.querySelectorAll('nav a[aria-current="page"]')];
                return {
                    h1Count: document.querySelectorAll('h1').length,
                    mainCount: document.querySelectorAll('main').length,
                    navsNamed: navs.length > 0 && navs.every((nav) => (nav.getAttribute('aria-label') || nav.getAttribute('aria-labelledby') || '').trim().length > 0),
                    linksNamed: links.every((link) => (link.innerText || '').trim() || (link.getAttribute('aria-label') || '').trim() || (link.getAttribute('aria-labelledby') || '').trim()),
                    currentNavCount: current.length,
                    headingLevels: levels,
                    skipLink: Boolean(document.querySelector('a.skip-link[href="#main-content"]')),
                    mainId: document.querySelector('main')?.id || null
                };
            }""")
            self.assertEqual(audit["h1Count"], 1, route)
            self.assertEqual(audit["mainCount"], 1, route)
            self.assertTrue(audit["navsNamed"], f"Unlabelled navigation landmark: {route}")
            self.assertTrue(audit["linksNamed"], f"Unnamed link: {route}")
            self.assertEqual(audit["currentNavCount"], 1, route)
            self.assertTrue(audit["skipLink"], route)
            self.assertEqual(audit["mainId"], "main-content", route)
            levels = audit["headingLevels"]
            self.assertTrue(all(current <= previous + 1 for previous, current in zip(levels, levels[1:])), f"Heading level jump: {route} {levels}")
            self.assertIn(expected_label, await page.title())
        await page.close()



    async def test_keyboard_skip_link_and_focus_on_each_route(self):
        page = await self.browser.new_page()
        for route in ("/", "/contact/"):
            await page.goto(self.base_url + route, wait_until="networkidle")
            await page.keyboard.press("Tab")
            focused = await page.evaluate("""() => {
                const el = document.activeElement;
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return {
                    href: el.getAttribute("href"),
                    visible: rect.width > 0 && rect.height > 0,
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                    boxShadow: style.boxShadow
                };
            }""")
            self.assertEqual(focused["href"], "#main-content", route)
            self.assertTrue(focused["visible"], route)
            focus_visible = (
                focused["outlineStyle"] not in ("none", "") and
                focused["outlineWidth"] not in ("0px", "")
            ) or focused["boxShadow"] != "none"
            self.assertTrue(focus_visible, f"No visible focus on skip link: {route} {focused}")
            await page.keyboard.press("Enter")
            self.assertEqual(await page.evaluate("window.location.hash"), "#main-content", route)
            self.assertTrue(await page.locator("#main-content").is_visible(), route)
        await page.close()

    async def test_reduced_motion_preference_is_respected(self):
        page = await self.browser.new_page(reduced_motion="reduce")
        await page.goto(self.base_url + "/", wait_until="networkidle")
        styles = await page.evaluate("""() => ({
            scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
            animationDuration: getComputedStyle(document.querySelector(".visual-core")).animationDuration,
            transitionDuration: getComputedStyle(document.querySelector(".visual-core")).transitionDuration
        })""")
        self.assertEqual(styles["scrollBehavior"], "auto")
        self.assertTrue(
            all(float(value.strip().removesuffix("s")) <= 0.00001
                for value in styles["animationDuration"].split(",")),
            f"Reduced-motion animation duration too long: {styles}"
        )
        self.assertTrue(
            all(float(value.strip().removesuffix("s")) <= 0.00001
                for value in styles["transitionDuration"].split(",")),
            f"Reduced-motion transition duration too long: {styles}"
        )
        await page.close()



    async def test_local_performance_budgets_and_network_isolation(self):
        page = await self.browser.new_page()
        requests = []
        failed = []
        page.on("request", lambda request: requests.append(request.url))
        page.on("requestfailed", lambda request: failed.append(request.url))
        for route in ("/", "/contact/"):
            requests.clear()
            failed.clear()
            response = await page.goto(self.base_url + route, wait_until="networkidle")
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200, route)
            metrics = await page.evaluate("""async () => {
                const resources = performance.getEntriesByType("resource");
                const navigation = performance.getEntriesByType("navigation")[0];
                const cssLink = document.querySelector('link[rel="stylesheet"]');
                const cssResponse = await fetch(cssLink.href, {cache: "no-store"});
                const cssBytes = new TextEncoder().encode(await cssResponse.text()).length;
                return {
                    htmlBytes: navigation ? navigation.encodedBodySize : 0,
                    resourceCount: resources.length,
                    domNodes: document.querySelectorAll("*").length,
                    cssBytes,
                    resourceUrls: resources.map((entry) => entry.name)
                };
            }""")
            self.assertLessEqual(metrics["htmlBytes"], 100_000, f"HTML budget exceeded: {route} {metrics}")
            self.assertLessEqual(metrics["cssBytes"], 100_000, f"CSS budget exceeded: {route} {metrics}")
            self.assertLessEqual(metrics["resourceCount"] + 1, 4, f"Request budget exceeded: {route} {metrics}")
            self.assertLessEqual(metrics["domNodes"], 500, f"DOM budget exceeded: {route} {metrics}")
            self.assertEqual(failed, [], f"Failed requests on {route}: {failed}")
            external = [url for url in requests if not url.startswith(self.base_url)]
            self.assertEqual(external, [], f"Third-party requests on {route}: {external}")
            self.assertTrue(all(url.startswith(self.base_url) for url in metrics["resourceUrls"]), metrics)
        await page.close()

    async def test_accessibility_landmarks_names_skip_link_and_keyboard_focus(self):
        page = await self.browser.new_page()
        response = await page.goto(self.base_url + "/", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)

        structure = await page.evaluate("""() => {
            const main = document.querySelector('main');
            const nav = document.querySelector('nav');
            const h1 = document.querySelectorAll('h1');
            const skip = [...document.querySelectorAll('a[href="#main-content"]')];
            const links = [...document.querySelectorAll('a')];
            const unnamedLinks = links.filter((link) =>
                !(link.innerText || '').trim() &&
                !link.getAttribute('aria-label') &&
                !link.getAttribute('aria-labelledby')
            );
            return {
                main: Boolean(main),
                nav: Boolean(nav),
                h1Count: h1.length,
                skipLinkCount: skip.length,
                unnamedLinks: unnamedLinks.length,
                mainId: main && main.id
            };
        }""")
        self.assertTrue(structure["main"], "Missing main landmark")
        self.assertTrue(structure["nav"], "Missing navigation landmark")
        self.assertEqual(structure["h1Count"], 1, "Expected exactly one H1")
        self.assertEqual(structure["mainId"], "main-content")
        self.assertGreater(structure["skipLinkCount"], 0, "Missing skip link to main content")
        self.assertEqual(structure["unnamedLinks"], 0, "Found links without accessible names")

        await page.keyboard.press("Tab")
        first_focus = await page.evaluate("""() => {
            const el = document.activeElement;
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName,
                href: el.getAttribute('href'),
                visible: rect.width > 0 && rect.height > 0,
                outlineStyle: style.outlineStyle,
                outlineWidth: style.outlineWidth,
                boxShadow: style.boxShadow
            };
        }""")
        self.assertEqual(first_focus["tag"], "A", "First keyboard stop should be a link")
        self.assertTrue(first_focus["visible"], "Keyboard focus target is not visible")
        has_focus_indicator = (
            first_focus["outlineStyle"] not in ("none", "") and
            first_focus["outlineWidth"] not in ("0px", "")
        ) or first_focus["boxShadow"] != "none"
        self.assertTrue(has_focus_indicator, f"No visible focus indicator: {first_focus}")
        await page.close()


    async def test_visual_layout_contract_across_viewports(self):
        """Guard key visual geometry and typography without claiming pixel-diff coverage."""
        page = await self.browser.new_page()
        viewports = (("mobile", 390, 844), ("tablet", 768, 1024), ("desktop", 1440, 900))
        for label, width, height in viewports:
            await page.set_viewport_size({"width": width, "height": height})
            response = await page.goto(self.base_url + "/", wait_until="networkidle")
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200, label)
            metrics = await page.evaluate("""() => {
                const rect = (selector) => {
                    const element = document.querySelector(selector);
                    if (!element) return null;
                    const box = element.getBoundingClientRect();
                    const style = getComputedStyle(element);
                    return {
                        width: box.width, height: box.height,
                        fontSize: parseFloat(style.fontSize),
                        color: style.color, background: style.backgroundColor
                    };
                };
                return {
                    viewport: document.documentElement.clientWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    header: rect(".site-header"),
                    hero: rect(".hero"),
                    heroVisual: rect(".hero-visual"),
                    heading: rect(".hero h1"),
                    cards: [...document.querySelectorAll(".feature-card")].map((el) => {
                        const box = el.getBoundingClientRect();
                        return {width: box.width, height: box.height};
                    })
                };
            }""")
            self.assertLessEqual(metrics["documentWidth"], metrics["viewport"] + 1, f"{label}: horizontal overflow {metrics}")
            self.assertIsNotNone(metrics["header"], f"{label}: missing header")
            self.assertIsNotNone(metrics["hero"], f"{label}: missing hero")
            self.assertIsNotNone(metrics["heroVisual"], f"{label}: missing visual hero")
            self.assertIsNotNone(metrics["heading"], f"{label}: missing hero heading")
            self.assertGreater(metrics["header"]["height"], 40, f"{label}: header collapsed")
            self.assertGreater(metrics["hero"]["height"], 180, f"{label}: hero collapsed")
            self.assertGreater(metrics["heroVisual"]["width"], 100, f"{label}: hero visual too narrow")
            self.assertGreater(metrics["heroVisual"]["height"], 100, f"{label}: hero visual too short")
            self.assertGreater(metrics["heading"]["fontSize"], 24, f"{label}: heading typography too small")
            self.assertEqual(len(metrics["cards"]), 3, f"{label}: expected three feature cards")
            self.assertTrue(all(card["width"] > 0 and card["height"] > 0 for card in metrics["cards"]), f"{label}: invisible feature card")
        await page.close()


    async def test_component_design_tokens_spacing_and_non_overlap(self):
        """Check computed component styles, hierarchy and layout ordering at three widths."""
        page = await self.browser.new_page()
        viewports = (("mobile", 390, 844, 1), ("tablet", 768, 1024, 1), ("desktop", 1440, 900, 3))
        for label, width, height, expected_columns in viewports:
            await page.set_viewport_size({"width": width, "height": height})
            response = await page.goto(self.base_url + "/", wait_until="networkidle")
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200, label)
            audit = await page.evaluate("""() => {
                const style = (selector) => getComputedStyle(document.querySelector(selector));
                const box = (element) => {
                    const r = element.getBoundingClientRect();
                    return {left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height};
                };
                const grid = document.querySelector(".feature-grid");
                const cards = [...document.querySelectorAll(".feature-card")];
                const heading = document.querySelector(".hero h1");
                const cardStyle = getComputedStyle(cards[0]);
                return {
                    ink: style("body").getPropertyValue("--ink").trim(),
                    accent: style("body").getPropertyValue("--accent").trim(),
                    paper: style("body").getPropertyValue("--paper").trim(),
                    bodyFont: style("body").fontFamily,
                    headingFont: getComputedStyle(heading).fontFamily,
                    headingSize: parseFloat(getComputedStyle(heading).fontSize),
                    headingWeight: Number(getComputedStyle(heading).fontWeight),
                    gridColumns: getComputedStyle(grid).gridTemplateColumns.split(" ").length,
                    gridGap: parseFloat(getComputedStyle(grid).columnGap),
                    cardPadding: parseFloat(cardStyle.paddingTop),
                    cardRadius: parseFloat(cardStyle.borderTopLeftRadius),
                    cardBorder: parseFloat(cardStyle.borderTopWidth),
                    cards: cards.map(box),
                    hero: box(document.querySelector(".hero")),
                    features: box(document.querySelector(".features"))
                };
            }""")
            self.assertRegex(audit["ink"], r"^#[0-9a-fA-F]{6}$", f"{label}: missing ink token")
            self.assertRegex(audit["accent"], r"^#[0-9a-fA-F]{6}$", f"{label}: missing accent token")
            self.assertRegex(audit["paper"], r"^#[0-9a-fA-F]{6}$", f"{label}: missing surface token")
            self.assertTrue(audit["bodyFont"] and audit["headingFont"], f"{label}: missing local font stack")
            self.assertGreaterEqual(audit["headingSize"], 24, f"{label}: heading hierarchy collapsed")
            self.assertGreaterEqual(audit["headingWeight"], 600, f"{label}: heading weight too light")
            self.assertEqual(audit["gridColumns"], expected_columns, f"{label}: unexpected feature grid columns")
            self.assertGreater(audit["gridGap"], 0, f"{label}: missing grid spacing")
            self.assertGreaterEqual(audit["cardPadding"], 16, f"{label}: card padding too small")
            self.assertGreaterEqual(audit["cardRadius"], 8, f"{label}: card radius missing")
            self.assertGreater(audit["cardBorder"], 0, f"{label}: card boundary missing")
            self.assertEqual(len(audit["cards"]), 3, f"{label}: expected three cards")
            for first, second in zip(audit["cards"], audit["cards"][1:]):
                overlaps = first["left"] < second["right"] and first["right"] > second["left"] and first["top"] < second["bottom"] and first["bottom"] > second["top"]
                self.assertFalse(overlaps, f"{label}: adjacent cards overlap: {first}, {second}")
                if expected_columns == 3:
                    self.assertLess(first["left"], second["left"], f"{label}: desktop card order changed")
                else:
                    self.assertLess(first["top"], second["top"], f"{label}: mobile/tablet card order changed")
            self.assertGreaterEqual(audit["features"]["top"], audit["hero"]["bottom"] - 1, f"{label}: feature section overlaps hero")
        await page.close()

if __name__ == "__main__":
    unittest.main()
