import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.image_provider_registry import ImageProviderRegistry, ModelProfile, ProviderProfile
from papi_core.papi_kids_orchestrator import prepare_pkp0001_from_project_sources
from papi_core.papi_kids_image_provider import MODEL_ID
from papi_core.papi_kids_editorial_approval import (
    EditorialApprovalError,
    build_pkp0001_editorial_preview_reader,
    build_postgres_editorial_approval_handler,
)


UPLOAD_ID = "PKP-UP-" + "e" * 32


class FakeCursor:
    def __init__(self):
        self.sql = ""
        self.params = None
        self.closed = False
    def execute(self, sql, params):
        self.sql = sql
        self.params = params
    def fetchone(self):
        return ("book-uuid",)
    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False
    def cursor(self):
        return self.cursor_instance
    def commit(self):
        self.committed = True
    def rollback(self):
        self.rolled_back = True
    def close(self):
        self.closed = True


class PapiKidsEditorialApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "private"
        self.root.mkdir()
        self.project = Path(self.temporary.name) / "project"
        source = self.project / "publishing" / "papi-kids" / "PKP-0001"
        source.mkdir(parents=True)
        repository_sources = Path(__file__).resolve().parents[1] / "publishing" / "papi-kids" / "PKP-0001"
        self.source_bytes = {}
        for name in ("manuscript-v2.md", "character-bible-v1.md",
                     "storyboard-v1.md", "illustration-prompts-24-v1.md",
                     "character-bible-prompt-compact-v1.md"):
            raw = (repository_sources / name).read_bytes()
            (source / name).write_bytes(raw)
            self.source_bytes[name] = raw
        self.upload_dir = self.root / UPLOAD_ID
        self.upload_dir.mkdir()
        manuscript = self.source_bytes["manuscript-v2.md"]
        (self.upload_dir / "manuscript.md").write_bytes(manuscript)
        digest = hashlib.sha256(manuscript).hexdigest()
        (self.upload_dir / "metadata.json").write_text(json.dumps({
            "upload_id": UPLOAD_ID, "sha256": digest, "status": "analysis_ready",
        }), encoding="utf-8")
        (self.upload_dir / "job.json").write_text(json.dumps({
            "upload_id": UPLOAD_ID, "source_sha256": digest,
            "stored_filename": "manuscript.md", "status": "analysis_ready",
        }), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_preview_is_bound_to_uploaded_v2_and_contains_24_prompts(self):
        reader = build_pkp0001_editorial_preview_reader(self.root, project_root=self.project)
        preview = reader(UPLOAD_ID)
        self.assertTrue(preview["source_match"])
        self.assertTrue(preview["approval_eligible"])
        self.assertEqual(preview["page_count"], 24)
        self.assertEqual([item["page_number"] for item in preview["prompts"]], list(range(1, 25)))
        self.assertEqual(len(preview["source_bundle_sha256"]), 64)


    def test_preview_bundle_hash_matches_generation_orchestrator(self):
        reader = build_pkp0001_editorial_preview_reader(self.root, project_root=self.project)
        preview = reader(UPLOAD_ID)
        registry = ImageProviderRegistry(
            providers=[ProviderProfile("cloudflare", "Cloudflare", "https://developers.cloudflare.com/workers-ai/platform/pricing", "verified", "account_api", True)],
            models=[ModelProfile("cloudflare", MODEL_ID, "image", 58, True, True, True)],
        )
        now = "2026-11-15T22:00:00+00:00"
        evidence = {
            "provider": "cloudflare", "account_ref": "a" * 32, "model_id": MODEL_ID,
            "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing",
            "evidence_ref": "quota-snapshot-001", "verified_at": now,
            "expires_at": "2026-11-15T23:00:00+00:00",
            "daily_quota_units": 10000, "spend_cap_minor": 0,
        }
        prepared = prepare_pkp0001_from_project_sources(
            project_root=self.project, registry=registry,
            account_refs={"cloudflare": "a" * 32},
            quota_evidence_by_model={MODEL_ID: evidence},
        )
        self.assertEqual(preview["source_bundle_sha256"], prepared["source_bundle_sha256"])
        self.assertTrue(all(len(page["prompt"]) <= 2048 for page in prepared["campaign"].batches[0].items))

    def test_different_uploaded_manuscript_cannot_be_approved(self):
        changed = b"# A different manuscript\n"
        (self.upload_dir / "manuscript.md").write_bytes(changed)
        digest = hashlib.sha256(changed).hexdigest()
        metadata = json.loads((self.upload_dir / "metadata.json").read_text())
        metadata["sha256"] = digest
        (self.upload_dir / "metadata.json").write_text(json.dumps(metadata))
        job = json.loads((self.upload_dir / "job.json").read_text())
        job["source_sha256"] = digest
        (self.upload_dir / "job.json").write_text(json.dumps(job))
        reader = build_pkp0001_editorial_preview_reader(self.root, project_root=self.project)
        preview = reader(UPLOAD_ID)
        self.assertFalse(preview["source_match"])
        self.assertFalse(preview["approval_eligible"])

    def test_approval_is_persisted_in_postgres_and_private_metadata(self):
        connection = FakeConnection()
        reader = build_pkp0001_editorial_preview_reader(self.root, project_root=self.project)
        preview = reader(UPLOAD_ID)
        handler = build_postgres_editorial_approval_handler(
            lambda: connection, preview_reader=reader,
            storage_root=self.root, reviewer_id="editor-01",
        )
        approval = handler(UPLOAD_ID, {
            "approved": True, "source_bundle_sha256": preview["source_bundle_sha256"],
        })
        self.assertTrue(approval["approved"])
        self.assertEqual(approval["reviewer_id"], "editor-01")
        self.assertTrue(connection.committed)
        self.assertIn("jsonb_set", connection.cursor_instance.sql)
        metadata = json.loads((self.upload_dir / "metadata.json").read_text())
        self.assertEqual(metadata["editorial_approval"]["source_bundle_sha256"],
                         preview["source_bundle_sha256"])

    def test_stale_preview_hash_is_rejected(self):
        connection = FakeConnection()
        reader = build_pkp0001_editorial_preview_reader(self.root, project_root=self.project)
        handler = build_postgres_editorial_approval_handler(
            lambda: connection, preview_reader=reader,
            storage_root=self.root, reviewer_id="editor-01",
        )
        with self.assertRaises(EditorialApprovalError):
            handler(UPLOAD_ID, {"approved": True, "source_bundle_sha256": "0" * 64})
        self.assertFalse(connection.committed)


if __name__ == "__main__":
    unittest.main()
