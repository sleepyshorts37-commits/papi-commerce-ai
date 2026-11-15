"""EPUB 3 fixed-layout generator for KDP children's picture books with text pop-ups."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
from xml.sax.saxutils import escape

from .papi_kids_asset_store import inspect_image


class KDPFixedLayoutEPUBError(ValueError):
    """Fixed-layout EPUB failed KDP validation."""


_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_EXT = {"image/png": ".png", "image/jpeg": ".jpg"}


def _verified_asset(root: Path, asset: dict[str, Any], *, prefix: str, min_width: int,
                    min_height: int, label: str) -> tuple[Path, str, int, int]:
    if not isinstance(asset, dict) or asset.get("review_status") != "approved":
        raise KDPFixedLayoutEPUBError(f"Illustration {label} non approuvée.")
    key = asset.get("storage_key", "")
    if not isinstance(key, str) or not key.startswith(prefix) or ".." in Path(key).parts:
        raise KDPFixedLayoutEPUBError(f"Chemin privé invalide pour {label}.")
    path = (root / key).resolve()
    if root not in path.parents or not path.is_file():
        raise KDPFixedLayoutEPUBError(f"Fichier image absent pour {label}.")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != asset.get("sha256") or not _SHA256.fullmatch(digest):
        raise KDPFixedLayoutEPUBError(f"SHA-256 incorrect pour {label}.")
    media_type = asset.get("media_type")
    if media_type not in _MEDIA_EXT:
        raise KDPFixedLayoutEPUBError(f"Format non pris en charge pour {label}.")
    width, height = inspect_image(data, media_type)
    if (width, height) != (asset.get("width_px"), asset.get("height_px")):
        raise KDPFixedLayoutEPUBError(f"Dimensions enregistrées incorrectes pour {label}.")
    if width < min_width or height < min_height:
        raise KDPFixedLayoutEPUBError(f"Résolution insuffisante pour {label}.")
    return path, media_type, width, height


def _validate_box(box: Any, page_number: int) -> tuple[float, float, float, float]:
    if not isinstance(box, dict):
        raise KDPFixedLayoutEPUBError(f"Zone de texte manquante page {page_number}.")
    try:
        x, y, width, height = (float(box[k]) for k in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError) as exc:
        raise KDPFixedLayoutEPUBError(f"Zone de texte invalide page {page_number}.") from exc
    if x < 5 or y < 5 or width <= 0 or height <= 0 or x + width > 90 or y + height > 85:
        raise KDPFixedLayoutEPUBError(
            f"Zone de texte/pop-up trop proche d'un bord page {page_number}."
        )
    return x, y, width, height


def build_kdp_fixed_layout_epub(
    storage_root: str | Path,
    output_path: str | Path,
    *,
    upload_id: str,
    title: str,
    author: str,
    language: str,
    identifier: str,
    modified_at: str,
    pages: list[dict[str, Any]],
    page_assets: list[dict[str, Any]],
    cover_asset: dict[str, Any],
    canvas_width_px: int = 2550,
    canvas_height_px: int = 2550,
    font_path: str | Path,
) -> dict[str, Any]:
    """Create a single-XHTML-page-per-page EPUB 3 with KDP Region Magnification."""
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise KDPFixedLayoutEPUBError("Référence de dépôt invalide.")
    if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
        raise KDPFixedLayoutEPUBError("Titre et auteur confirmés obligatoires.")
    if language != "fr" or not isinstance(identifier, str) or not identifier.strip():
        raise KDPFixedLayoutEPUBError("Langue ou identifiant EPUB invalide.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", modified_at):
        raise KDPFixedLayoutEPUBError("Date de modification ISO 8601 UTC requise.")
    if not isinstance(canvas_width_px, int) or not isinstance(canvas_height_px, int):
        raise KDPFixedLayoutEPUBError("Résolution originale invalide.")
    if not (1 <= canvas_width_px <= 10000 and 1 <= canvas_height_px <= 10000):
        raise KDPFixedLayoutEPUBError("Résolution originale hors limites.")
    if not isinstance(pages, list) or not isinstance(page_assets, list) or len(pages) < 1 or len(pages) != len(page_assets):
        raise KDPFixedLayoutEPUBError("Chaque page doit avoir un texte et une illustration.")
    if not Path(font_path).is_file() or Path(font_path).suffix.lower() not in {".ttf", ".otf"}:
        raise KDPFixedLayoutEPUBError("Police incorporable TrueType/OpenType manquante.")
    if len(title) > 200 or len(author) > 120:
        raise KDPFixedLayoutEPUBError("Titre ou auteur trop long.")

    root = Path(storage_root).resolve()
    cover_path, cover_type, cover_width, cover_height = _verified_asset(
        root, cover_asset, prefix="covers/", min_width=canvas_width_px,
        min_height=canvas_height_px, label="couverture",
    )
    if abs(cover_width / cover_height - canvas_width_px / canvas_height_px) > 0.005:
        raise KDPFixedLayoutEPUBError("Ratio de couverture incompatible avec la résolution EPUB.")

    assets_by_page: dict[int, dict[str, Any]] = {}
    for asset in page_assets:
        number = asset.get("page_number") if isinstance(asset, dict) else None
        if not isinstance(number, int) or number in assets_by_page:
            raise KDPFixedLayoutEPUBError("Pages d'illustration dupliquées ou invalides.")
        assets_by_page[number] = asset
    if sorted(assets_by_page) != list(range(1, len(pages) + 1)):
        raise KDPFixedLayoutEPUBError("Une illustration approuvée est requise pour chaque page.")

    validated_pages = []
    for number, page in enumerate(pages, start=1):
        if not isinstance(page, dict) or page.get("page_number") != number:
            raise KDPFixedLayoutEPUBError("Pages de texte désordonnées.")
        text = page.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 3000:
            raise KDPFixedLayoutEPUBError(f"Texte vide ou trop long page {number}.")
        box = _validate_box(page.get("text_box"), number)
        path, media_type, width, height = _verified_asset(
            root, assets_by_page[number], prefix=f"{upload_id}/illustrations/",
            min_width=canvas_width_px, min_height=canvas_height_px, label=f"page {number}",
        )
        if abs(width / height - canvas_width_px / canvas_height_px) > 0.005:
            raise KDPFixedLayoutEPUBError(f"Ratio image incompatible page {number}.")
        validated_pages.append((page, path, media_type, box))

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".papi-epub-", suffix=".epub", dir=output.parent)
    os.close(fd)
    font_name = Path(font_path).name
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "-", identifier)[:180]
    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/book.css" media-type="text/css"/>',
        f'<item id="font" href="fonts/{escape(font_name)}" media-type="{"font/otf" if Path(font_name).suffix.lower() == ".otf" else "font/ttf"}"/>',
        f'<item id="cover-image" href="images/cover{_MEDIA_EXT[cover_type]}" media-type="{cover_type}" properties="cover-image"/>',
        '<item id="cover-page" href="pages/cover.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine_items = ['<itemref idref="cover-page" linear="yes"/>']
    page_documents: list[tuple[str, bytes]] = []
    for number, (page, path, media_type, box) in enumerate(validated_pages, start=1):
        page_id = f"page-{number:03d}"
        extension = _MEDIA_EXT[media_type]
        manifest_items.append(
            f'<item id="{page_id}-image" href="images/{page_id}{extension}" media-type="{media_type}"/>'
        )
        manifest_items.append(
            f'<item id="{page_id}" href="pages/{page_id}.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="{page_id}" linear="yes"/>')
        x, y, width, height = box
        source_id = f"{page_id}-source"
        target_id = f"{page_id}-target"
        text = escape(page["text"]).replace("\n", "<br/>")
        doc = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="fr" lang="fr">
<head><title>{escape(title)} — page {number}</title><meta name="viewport" content="width={canvas_width_px},height={canvas_height_px}"/><link rel="stylesheet" type="text/css" href="../styles/book.css"/></head>
<body><div class="page" style="width:{canvas_width_px}px;height:{canvas_height_px}px">
<img class="background" src="../images/{page_id}{extension}" alt="Illustration de la page {number}"/>
<div class="text-source" style="left:{x}%;top:{y}%;width:{width}%;height:{height}%">
<a class="app-amzn-magnify" data-app-amzn-magnify='{{"targetId":"{target_id}","sourceId":"{source_id}","ordinal":{number}}}'>
<p id="{source_id}" class="story-text">{text}</p></a></div>
<div id="{target_id}" class="target-mag" style="left:{x}%;top:{y}%;width:{width}%;height:{height}%"></div>
</div></body></html>"""
        page_documents.append((f"OEBPS/pages/{page_id}.xhtml", doc.encode("utf-8")))

    cover_doc = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr" lang="fr">
<head><title>{escape(title)} — couverture</title><meta name="viewport" content="width={canvas_width_px},height={canvas_height_px}"/><link rel="stylesheet" type="text/css" href="../styles/book.css"/></head>
<body><div class="page cover-page" style="width:{canvas_width_px}px;height:{canvas_height_px}px">
<img class="background" src="../images/cover{_MEDIA_EXT[cover_type]}" alt="Couverture de {escape(title)}"/>
<div class="cover-title">{escape(title)}</div><div class="cover-author">{escape(author)}</div>
</div></body></html>"""
    page_documents.append(("OEBPS/pages/cover.xhtml", cover_doc.encode("utf-8")))

    nav = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="fr" lang="fr">
<head><title>Sommaire</title></head><body><nav epub:type="toc" id="toc"><h1>Sommaire</h1><ol>
<li><a href="pages/cover.xhtml">Couverture</a></li>
{''.join(f'<li><a href="pages/page-{n:03d}.xhtml">Page {n}</a></li>' for n in range(1, len(pages)+1))}
</ol></nav></body></html>"""
    css = f"""@font-face{{font-family:BookFont;src:url('../fonts/{font_name}');}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:100%;height:100%;overflow:hidden;background:#fff;}}
.page{{position:relative;width:{canvas_width_px}px;height:{canvas_height_px}px;overflow:hidden;}}
.background{{position:absolute;left:0;top:0;width:100%;height:100%;}}
.text-source{{position:absolute;z-index:2;overflow:hidden;}}
.story-text{{font-family:BookFont,sans-serif;font-size:4.2vw;line-height:1.25;color:#111;background:rgba(255,255,255,.82);padding:1.5%;}}
.target-mag{{position:absolute;z-index:3;background:rgba(255,255,255,.96);}}
.cover-title{{position:absolute;left:10%;top:12%;width:80%;font-family:BookFont,sans-serif;font-size:6vw;line-height:1.1;text-align:center;color:#14233a;}}
.cover-author{{position:absolute;left:10%;bottom:8%;width:80%;font-family:BookFont,sans-serif;font-size:3.2vw;text-align:center;color:#14233a;}}
"""
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="fr" prefix="rendition: http://www.idpf.org/vocab/rendition/#">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="pub-id">{escape(safe_id)}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator><dc:language>fr</dc:language>
<meta property="dcterms:modified">{modified_at}</meta>
<meta property="rendition:layout">pre-paginated</meta><meta property="rendition:orientation">auto</meta>
<meta name="original-resolution" content="{canvas_width_px}x{canvas_height_px}"/>
<meta name="book-type" content="children"/><meta name="primary-writing-mode" content="horizontal-lr"/>
</metadata><manifest>{''.join(manifest_items)}</manifest>
<spine page-progression-direction="ltr">{''.join(spine_items)}</spine></package>"""
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    try:
        with ZipFile(temporary_name, "w") as archive:
            mime = ZipInfo("mimetype")
            mime.compress_type = ZIP_STORED
            archive.writestr(mime, "application/epub+zip")
            archive.writestr("META-INF/container.xml", container, compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/package.opf", opf, compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/nav.xhtml", nav, compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/styles/book.css", css, compress_type=ZIP_DEFLATED)
            archive.write(font_path, f"OEBPS/fonts/{font_name}", compress_type=ZIP_DEFLATED)
            archive.write(cover_path, f"OEBPS/images/cover{_MEDIA_EXT[cover_type]}", compress_type=ZIP_DEFLATED)
            for number, (page, path, media_type, box) in enumerate(validated_pages, start=1):
                archive.write(path, f"OEBPS/images/page-{number:03d}{_MEDIA_EXT[media_type]}", compress_type=ZIP_DEFLATED)
            for name, data in page_documents:
                archive.writestr(name, data, compress_type=ZIP_DEFLATED)
        with ZipFile(temporary_name, "r") as archive:
            if archive.testzip() is not None or archive.namelist()[0] != "mimetype":
                raise KDPFixedLayoutEPUBError("Archive EPUB corrompue ou mimetype mal placé.")
            if archive.read("mimetype") != b"application/epub+zip":
                raise KDPFixedLayoutEPUBError("Mimetype EPUB invalide.")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, output)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return {
        "output_path": str(output),
        "format": "EPUB 3",
        "layout": "pre-paginated",
        "page_count": len(pages),
        "text_popups": True,
        "embedded_font": True,
        "approved_assets_only": True,
        "kdp_upload_ready": False,
        "kindle_previewer_required": True,
        "source_url": "https://kdp.amazon.com/help/topic/GFFHCXVPHRZW8SJ5",
    }
