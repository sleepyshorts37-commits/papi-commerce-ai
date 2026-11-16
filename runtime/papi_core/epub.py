"""Génération d'un paquet EPUB 3 minimal depuis un manuscrit validé."""
from __future__ import annotations

import hashlib
import html
import io
import uuid
import zipfile
from datetime import datetime, timezone

from .manuscript import validate_manuscript


class EpubError(ValueError):
    """Erreur de préparation du paquet EPUB."""


_CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""
_CSS = """body { font-family: serif; line-height: 1.5; margin: 5%; }
h1, h2 { page-break-after: avoid; }
p { text-indent: 1em; }
"""
def _x(value: str) -> str:
    return html.escape(value, quote=True)


def build_epub(manuscript: dict) -> bytes:
    """Construit un EPUB 3 sans images ; le fichier doit encore passer le préflight KDP."""
    report = validate_manuscript(manuscript)
    title = _x(report.title)
    language = report.language
    identifier = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, report.content_sha256))
    chapters = manuscript["chapters"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/styles.css", _CSS, compress_type=zipfile.ZIP_DEFLATED)
        nav_items = []
        manifest_items = [
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="css" href="styles.css" media-type="text/css"/>',
            '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
        ]
        spine_items = ['<itemref idref="title"/>']
        title_page = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="' + language + '"><head>'
            '<title>' + title + '</title><link rel="stylesheet" type="text/css" href="styles.css"/>'
            '</head><body><h1>' + title + '</h1><h2>Synopsis</h2><p>'
            + _x(manuscript["synopsis"]) + '</p></body></html>'
        )
        archive.writestr("EPUB/title.xhtml", title_page, compress_type=zipfile.ZIP_DEFLATED)
        for index, chapter in enumerate(chapters, 1):
            filename = f"chapter-{index:03d}.xhtml"
            chap_title = _x(chapter["title"].strip())
            body = "".join("<p>" + _x(paragraph.strip()) + "</p>"
                           for paragraph in chapter["text"].strip().split("\n\n") if paragraph.strip())
            brief = chapter.get("illustration_brief", "")
            if brief:
                body += '<p class="illustration-note">' + _x(brief.strip()) + "</p>"
            content = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<html xmlns="http://www.w3.org/1999/xhtml" lang="' + language + '"><head>'
                '<title>' + chap_title + '</title><link rel="stylesheet" type="text/css" href="styles.css"/>'
                '</head><body><h1>' + chap_title + '</h1>' + body + '</body></html>'
            )
            archive.writestr("EPUB/" + filename, content, compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append(
                f'<item id="ch{index}" href="{filename}" media-type="application/xhtml+xml"/>'
            )
            spine_items.append(f'<itemref idref="ch{index}"/>')
            nav_items.append(f'<li><a href="{filename}">{chap_title}</a></li>')
        nav = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" lang="' + language + '"><head>'
            '<title>Sommaire</title></head><body><nav epub:type="toc" id="toc"><h1>Sommaire</h1><ol>'
            + "".join(nav_items) + '</ol></nav></body></html>'
        )
        archive.writestr("EPUB/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        opf = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:identifier id="bookid">' + identifier + '</dc:identifier>'
            '<dc:title>' + title + '</dc:title><dc:language>' + language + '</dc:language>'
            '<meta property="dcterms:modified">' + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            + '</meta></metadata><manifest>' + "".join(manifest_items)
            + '<item id="navfile" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
            + '</manifest><spine>' + "".join(spine_items)
            + '</spine></package>'
        )
        archive.writestr("EPUB/package.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
    result = buffer.getvalue()
    if not result.startswith(b"PK"):
        raise EpubError("Le paquet EPUB n'a pas pu être assemblé.")
    return result


def inspect_epub(content: bytes) -> dict:
    """Contrôle minimal de l'archive ; ne remplace pas EPUBCheck ni le préflight KDP."""
    if not isinstance(content, bytes) or not content:
        raise EpubError("Contenu EPUB absent.")
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
            names = archive.namelist()
            if not names or names[0] != "mimetype":
                raise EpubError("Le fichier mimetype doit être le premier élément EPUB.")
            if archive.read("mimetype") != b"application/epub+zip":
                raise EpubError("Type MIME EPUB invalide.")
            required = {"META-INF/container.xml", "EPUB/package.opf", "EPUB/nav.xhtml", "EPUB/title.xhtml"}
            if not required.issubset(set(names)):
                raise EpubError("Fichiers obligatoires EPUB manquants.")
            if archive.testzip() is not None:
                raise EpubError("Archive EPUB corrompue.")
            return {
                "valid_archive": True,
                "entry_count": len(names),
                "sha256": hashlib.sha256(content).hexdigest(),
                "chapters": sum(name.startswith("EPUB/chapter-") and name.endswith(".xhtml") for name in names),
                "epubcheck_required": True,
                "kdp_preflight_required": True,
            }
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise EpubError("Archive EPUB illisible ou incomplète.") from exc
