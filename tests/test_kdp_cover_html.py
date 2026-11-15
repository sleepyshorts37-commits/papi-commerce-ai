import unittest

from papi_core.kdp_cover_html import KDPCoverRenderError, render_pkp0001_cover_html


def render(**overrides):
    args = {
        "full_wrap_image": b"\x89PNG\r\n\x1a\ncover",
        "image_mime_type": "image/png",
        "cover_width_in": 17.3,
        "cover_height_in": 8.75,
        "official_template_ref": "kdp-template-2026-11",
        "front_panel": {"x": 0.51, "y": 0, "width": 0.49, "height": 1},
        "back_panel": {"x": 0, "y": 0, "width": 0.48, "height": 1},
        "title": "Nia et la rivière aux mille reflets",
        "subtitle": "Une aventure au cœur du Sénégal",
        "back_blurb": "Nia observe la rivière et apprend à agir avec les adultes.",
        "author": "",
        "title_box": {"x": 0.58, "y": 0.08, "width": 0.34, "height": 0.3},
        "back_text_box": {"x": 0.05, "y": 0.2, "width": 0.35, "height": 0.4},
        "spine_box": {"x": 0.48, "y": 0.05, "width": 0.03, "height": 0.9},
    }
    args.update(overrides)
    return render_pkp0001_cover_html(**args)


class KDPCoverHTMLTests(unittest.TestCase):
    def test_renders_cover_with_editable_title_and_blurb(self):
        html = render()
        self.assertIn("Nia et la rivière aux mille reflets", html)
        self.assertIn("Nia observe la rivière", html)
        self.assertIn("data-template='kdp-template-2026-11'", html)
        self.assertIn("data:image/png;base64,", html)

    def test_author_is_optional_and_not_invented(self):
        html = render(author="")
        self.assertNotIn("Khaly", html)

    def test_rejects_missing_art_and_template_reference(self):
        with self.assertRaises(KDPCoverRenderError):
            render(full_wrap_image=b"")
        with self.assertRaises(KDPCoverRenderError):
            render(official_template_ref="")

    def test_rejects_title_outside_front_panel(self):
        with self.assertRaises(KDPCoverRenderError):
            render(title_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2})

    def test_escapes_cover_text(self):
        html = render(title="<script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
