import unittest

from papi_core.kdp_interior_html import (
    KDPInteriorRenderError, parse_manuscript_pages, render_pkp0001_interior_html,
)


def manuscript():
    return "\n\n".join(
        f"### Page {i} — Titre {i}\nTexte de narration page {i}.\n\nDialogue."
        for i in range(1, 25)
    )


def assets():
    return {f"page-{i:02d}": {"image_bytes": b"\x89PNG\r\n\x1a\nfake", "mime_type": "image/png"}
            for i in range(1, 25)}


def layouts():
    return {f"page-{i:02d}": {
        "x": 0.05, "y": 0.05, "width": 0.55, "height": 0.4,
        "font_size_pt": 18, "align": "left", "panel_opacity": 0.85,
    } for i in range(1, 25)}


class KDPInteriorHTMLTests(unittest.TestCase):
    def test_parses_exactly_24_pages(self):
        self.assertEqual(len(parse_manuscript_pages(manuscript())), 24)

    def test_renders_24_print_sized_pages_with_editable_text(self):
        html = render_pkp0001_interior_html(
            manuscript_markdown=manuscript(), images_by_page=assets(),
            page_width_in=8.5, page_height_in=8.5, layout_by_page=layouts())
        self.assertEqual(html.count('<section class="page"'), 24)
        self.assertIn("@page{size:8.5000in 8.5000in;margin:0}", html)
        self.assertIn("Texte de narration page 1.", html)
        self.assertIn("data:image/png;base64,", html)

    def test_rejects_missing_images_and_layouts(self):
        imgs = assets()
        imgs.pop("page-24")
        with self.assertRaises(KDPInteriorRenderError):
            render_pkp0001_interior_html(
                manuscript_markdown=manuscript(), images_by_page=imgs,
                page_width_in=8.5, page_height_in=8.5, layout_by_page=layouts())

    def test_rejects_text_box_outside_page(self):
        layout = layouts()
        layout["page-01"]["x"] = 0.8
        layout["page-01"]["width"] = 0.4
        with self.assertRaises(KDPInteriorRenderError):
            render_pkp0001_interior_html(
                manuscript_markdown=manuscript(), images_by_page=assets(),
                page_width_in=8.5, page_height_in=8.5, layout_by_page=layout)

    def test_escapes_manuscript_markup(self):
        source = manuscript().replace("Texte de narration page 1.", "<script>alert(1)</script>")
        html = render_pkp0001_interior_html(
            manuscript_markdown=source, images_by_page=assets(),
            page_width_in=8.5, page_height_in=8.5, layout_by_page=layouts())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
