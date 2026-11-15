"""Build a hash-verified, private ZIP for manual Amazon KDP submission."""
from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
import zipfile
from typing import Any, Callable

from .papi_kids_kdp_metadata import validate_kdp_listing_metadata


class PapiKidsSubmissionBundleError(ValueError):
    """The latest package is not authorized or an artifact failed integrity checks."""


def _private_file(root: Path, upload_id: str, relative: Any, expected_hash: Any) -> tuple[Path, bytes]:
    if (not isinstance(relative, str) or not relative or Path(relative).is_absolute()
            or ".." in Path(relative).parts or not Path(relative).parts
            or Path(relative).parts[0] != upload_id):
        raise PapiKidsSubmissionBundleError("Chemin d'artefact invalide.")
    candidate = root / relative
    if any(parent.is_symlink() for parent in [candidate, *candidate.parents] if parent != root):
        raise PapiKidsSubmissionBundleError("Lien symbolique interdit dans le dossier privé.")
    path = candidate.resolve()
    if root not in path.parents or not path.is_file():
        raise PapiKidsSubmissionBundleError("Fichier privé absent.")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or digest != expected_hash:
        raise PapiKidsSubmissionBundleError("Empreinte SHA-256 de l'artefact incorrecte.")
    return path, data


def build_private_kdp_submission_bundle(
    storage_root: str | Path,
    connection_factory: Callable[[], Any],
) -> Callable[[str], dict[str, Any]]:
    """Create an in-memory ZIP only for the latest package with matching owner sign-off."""
    raw_root = Path(storage_root)
    if raw_root.is_symlink():
        raise PapiKidsSubmissionBundleError("Le stockage privé ne peut pas être un lien symbolique.")
    root = raw_root.resolve()

    def build(upload_id: str) -> dict[str, Any]:
        if not isinstance(upload_id, str) or not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
            raise PapiKidsSubmissionBundleError("Référence de dépôt invalide.")
        connection = connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """select b.book_id, b.metadata, p.package_version, p.package_manifest,
                          p.package_manifest_sha256
                     from papi_kids_private.books b
                     join lateral (
                         select package_version, package_manifest, package_manifest_sha256
                           from papi_kids_private.kdp_package_builds
                          where upload_id = b.upload_id
                          order by package_version desc limit 1
                     ) p on true
                    where b.upload_id = %s""",
                (upload_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise PapiKidsSubmissionBundleError("Livre ou package introuvable.")
            book_id, metadata, version, manifest, manifest_sha256 = row
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            if isinstance(manifest, str):
                manifest = json.loads(manifest)
            metadata = metadata or {}
            if not isinstance(manifest, dict) or manifest.get("upload_id") != upload_id or manifest.get("package_version") != version:
                raise PapiKidsSubmissionBundleError("Manifeste KDP invalide.")
            canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            actual_manifest_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if actual_manifest_hash != manifest_sha256:
                raise PapiKidsSubmissionBundleError("Empreinte du manifeste KDP incorrecte.")
            authorization = metadata.get("kdp_owner_release_authorization") or {}
            if (authorization.get("package_version") != version
                    or authorization.get("manifest_sha256") != manifest_sha256
                    or authorization.get("manual_submission_only") is not True):
                raise PapiKidsSubmissionBundleError("Autorisation finale du propriétaire absente ou périmée.")
            cursor.execute(
                """select authorization_id from papi_kids_private.kdp_owner_release_authorizations
                    where upload_id = %s and package_version = %s and manifest_sha256 = %s
                      and owner_id = %s limit 1""",
                (upload_id, version, manifest_sha256, authorization.get("owner_id")),
            )
            if not cursor.fetchone():
                raise PapiKidsSubmissionBundleError("Preuve persistante de l'autorisation propriétaire absente.")
            package_reviews = metadata.get("kdp_package_reviews") or {}
            safety = metadata.get("content_safety_review") or {}
            if safety.get("approved") is not True:
                raise PapiKidsSubmissionBundleError("Validation sécurité jeunesse absente.")
            listing = metadata.get("kdp_listing_metadata") or {}
            listing_validation = validate_kdp_listing_metadata(listing, paperback=True)
            if listing_validation.get("blockers"):
                raise PapiKidsSubmissionBundleError("Fiche commerciale KDP incomplète.")
            if listing.get("commercial_use_confirmed") is not True:
                raise PapiKidsSubmissionBundleError("Droits d'exploitation commerciale non confirmés.")
            if manifest.get("spend_limit_minor") != 0:
                raise PapiKidsSubmissionBundleError("Le plafond de dépense doit être zéro.")

            files: dict[str, bytes] = {}
            pdfs = manifest.get("pdfs") or {}
            for artifact in ("interior", "cover"):
                record = pdfs.get(artifact)
                review = package_reviews.get(f"v{version}:{artifact}")
                if (not isinstance(record, dict) or not isinstance(review, dict)
                        or review.get("approved") is not True
                        or review.get("artifact_sha256") != record.get("sha256")
                        or review.get("package_version") != version):
                    raise PapiKidsSubmissionBundleError(f"Revue humaine périmée : {artifact}.")
                _, data = _private_file(root, upload_id, record.get("path"), record.get("sha256"))
                if not data.startswith(b"%PDF-"):
                    raise PapiKidsSubmissionBundleError(f"Fichier PDF invalide : {artifact}.")
                files[f"{artifact}.pdf"] = data
            ebook = manifest.get("ebook")
            if ebook:
                review = package_reviews.get(f"v{version}:ebook")
                preview = metadata.get("kindle_previewer_review") or {}
                if (not isinstance(review, dict) or review.get("approved") is not True
                        or review.get("artifact_sha256") != ebook.get("sha256")
                        or review.get("package_version") != version
                        or preview.get("passed") is not True
                        or preview.get("package_version") != version
                        or preview.get("epub_sha256") != ebook.get("sha256")):
                    raise PapiKidsSubmissionBundleError("Revue EPUB ou Kindle Previewer absente/périmée.")
                _, data = _private_file(root, upload_id, ebook.get("path"), ebook.get("sha256"))
                if not data.startswith(b"PK"):
                    raise PapiKidsSubmissionBundleError("Fichier EPUB invalide.")
                files["book.epub"] = data

            normalized_listing = listing_validation["normalized_draft"]
            attestation = {
                "package_version": version,
                "manifest_sha256": manifest_sha256,
                "artifact_reviews": {
                    key: {
                        "decision": value.get("decision"),
                        "approved": value.get("approved"),
                        "artifact_sha256": value.get("artifact_sha256"),
                        "reviewer_id": value.get("reviewer_id"),
                        "reviewed_at": value.get("reviewed_at"),
                        "evidence_ref": value.get("evidence_ref"),
                    }
                    for key, value in package_reviews.items()
                    if key.startswith(f"v{version}:") and isinstance(value, dict)
                },
                "kindle_previewer_review": {
                    key: (metadata.get("kindle_previewer_review") or {}).get(key)
                    for key in ("passed", "package_version", "epub_sha256", "reviewer_id", "reviewed_at", "evidence_ref")
                    if key in (metadata.get("kindle_previewer_review") or {})
                },
                "content_safety_review": {
                    key: safety.get(key) for key in ("approved", "reviewer_id", "reviewed_at", "evidence_ref", "manuscript_sha256")
                    if key in safety
                },
                "owner_release_authorization": {
                    key: authorization.get(key) for key in ("owner_id", "confirmed_at", "evidence_ref", "package_version", "manifest_sha256")
                    if key in authorization
                },
            }
            files["package-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            files["kdp-listing-metadata.json"] = (json.dumps(normalized_listing, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            files["review-attestations.json"] = (json.dumps(attestation, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            readme = (
                "PAPI KIDS — DOSSIER DE SOUMISSION MANUELLE AMAZON KDP\n\n"
                "Ce dossier contient les fichiers du package vérifié et les preuves d'approbation.\n"
                "Vérifiez chaque PDF dans un lecteur PDF et l'EPUB dans Kindle Previewer avant toute soumission.\n"
                "Connectez-vous vous-même à votre compte Amazon KDP et saisissez les métadonnées jointes.\n"
                "Aucun fichier n'a été téléversé à Amazon. Aucune publication n'a été effectuée.\n"
                "Vérifiez les règles KDP et les droits avant d'envoyer le dossier.\n"
            )
            files["README-SOUMISSION-MANUELLE.txt"] = readme.encode("utf-8")
            checksums = "".join(
                f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                for name, data in sorted(files.items())
            )
            files["SHA256SUMS.txt"] = checksums.encode("utf-8")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(files.items()):
                    archive.writestr(name, data)
            connection.commit()
            return {
                "data": buffer.getvalue(),
                "content_type": "application/zip",
                "filename": "papi-kids-kdp-submission.zip",
                "package_version": version,
                "manifest_sha256": manifest_sha256,
                "artifact_count": len(files),
                "publication_performed": False,
                "spend_limit_minor": 0,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()
    return build
