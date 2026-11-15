import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_reconciliation_signature import (
    ArtifactSignatureError,
    verify_reconciliation_artifact_signature,
)


# RFC 8032, section 7.1, test vector 2. Public key and signature only;
# the corresponding private key is deliberately not present or generated.
PUBLIC_KEY = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
SIGNATURE = (
    "92a009a9f0d4cab8720e820b5f642540"
    "a2b27b5416503f8fb3762223ebdb69da"
    "085ac1e43e15996e458f3613d0f11d8c"
    "387b2eaeb4302aeeb00d291612bb0c00"
)
SIGNED_BYTES = b"r"


class ReconciliationArtifactSignatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self.tmp.name) / "public-keys.json"
        self.write_registry()

    def tearDown(self):
        self.tmp.cleanup()

    def write_registry(self, status="active", version=1, history=None):
        record = {
            "status": status,
            "key_version": version,
            "public_key": PUBLIC_KEY if version == 1 else "00" * 32,
            "key_history": history or [],
        }
        self.registry.write_text(json.dumps({
            "schema_version": 1,
            "agents": {"agent-a": record},
        }), encoding="utf-8")

    def proof(self, **overrides):
        proof = {
            "schema_version": 1,
            "algorithm": "Ed25519",
            "agent_id": "agent-a",
            "key_version": 1,
            "artifact_sha256": hashlib.sha256(SIGNED_BYTES).hexdigest(),
            "signature": SIGNATURE,
        }
        proof.update(overrides)
        return proof

    def test_verifies_rfc8032_public_signature_vector(self):
        result = verify_reconciliation_artifact_signature(
            SIGNED_BYTES, self.proof(), self.registry
        )
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["nonce_consumed"])
        self.assertFalse(result["historical_key"])

    def test_rejects_artifact_digest_mismatch(self):
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                b"tampered", self.proof(), self.registry
            )

    def test_rejects_signature_tampering(self):
        altered = self.proof(signature="00" * 64)
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                SIGNED_BYTES, altered, self.registry
            )

    def test_rejects_unknown_key_version(self):
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                SIGNED_BYTES, self.proof(key_version=2), self.registry
            )

    def test_revoked_identity_is_auditable_but_never_authorized(self):
        self.write_registry(status="revoked")
        result = verify_reconciliation_artifact_signature(
            SIGNED_BYTES, self.proof(), self.registry
        )
        self.assertTrue(result["signature_verified"])
        self.assertEqual(result["identity_status"], "revoked")
        self.assertFalse(result["authorization_granted"])

    def test_rejects_wrong_algorithm_and_unknown_fields(self):
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                SIGNED_BYTES, self.proof(algorithm="RSA"), self.registry
            )
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                SIGNED_BYTES, self.proof(extra="unexpected"), self.registry
            )

    def test_rejects_non_bytes_and_oversized_artifacts(self):
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                "not bytes", self.proof(), self.registry
            )
        with self.assertRaises(ArtifactSignatureError):
            verify_reconciliation_artifact_signature(
                b"x" * (2 * 1024 * 1024 + 1), self.proof(), self.registry
            )


if __name__ == "__main__":
    unittest.main()
