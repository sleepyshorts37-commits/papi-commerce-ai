"""Tests PAPI CONNECT telemetry: local-only, privacy-safe and read-only."""
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.connect_observability import (
    ConnectorTelemetry,
    ConnectorTelemetryError,
    build_connector_usage_report,
)
from papi_core.connectors import ConnectorError, ConnectorGateway
from papi_core.providers import GenerationRequest


class ConnectorObservabilityTests(unittest.TestCase):
    def test_gateway_records_simulated_call_without_prompt_or_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            gateway = ConnectorGateway(telemetry=ConnectorTelemetry(ledger))
            prompt = "private prompt phrase that must not be stored"
            project_id = "private-project-reference"
            result = gateway.generate(
                "local.mock",
                GenerationRequest(project_id, "text", prompt),
                {"connectors.generate"},
            )
            self.assertTrue(result.simulated)
            raw = ledger.read_text(encoding="utf-8")
            self.assertNotIn(prompt, raw)
            self.assertNotIn(project_id, raw)
            self.assertNotIn(result.content, raw)
            report = build_connector_usage_report(ledger)
            self.assertEqual(report["totals"]["calls_started"], 1)
            self.assertEqual(report["totals"]["calls_completed"], 1)
            self.assertEqual(report["totals"]["simulated_completed"], 1)
            self.assertEqual(report["totals"]["estimated_cost_xof"], 0)
            self.assertEqual(report["totals"]["provider_reported_cost_xof"], 0)
            self.assertEqual(report["by_provider"]["local.mock"]["calls_completed"], 1)

    def test_adapter_failure_is_counted_without_private_diagnostic(self):
        class RaisingAdapter:
            name = "mock"
            supported_kinds = frozenset({"text", "image"})
            is_external = False
            credentials_env = None

            def generate(self, request):
                raise RuntimeError("private sdk diagnostic must not be logged")

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            gateway = ConnectorGateway(telemetry=ConnectorTelemetry(ledger))
            gateway._adapters["local.mock"] = RaisingAdapter()
            with self.assertRaisesRegex(ConnectorError, "Échec d'exécution"):
                gateway.generate(
                    "local.mock",
                    GenerationRequest("project-private", "text", "do not log"),
                    {"connectors.generate"},
                )
            raw = ledger.read_text(encoding="utf-8")
            self.assertNotIn("private sdk diagnostic", raw)
            self.assertNotIn("project-private", raw)
            report = build_connector_usage_report(ledger)
            self.assertEqual(report["totals"]["calls_failed"], 1)
            self.assertEqual(report["totals"]["calls_incomplete"], 0)

    def test_unavailable_start_ledger_blocks_adapter_execution(self):
        class CountingAdapter:
            name = "mock"
            supported_kinds = frozenset({"text", "image"})
            is_external = False
            credentials_env = None

            def __init__(self):
                self.calls = 0

            def generate(self, request):
                self.calls += 1
                raise AssertionError("must not execute")

        with tempfile.TemporaryDirectory() as tmp:
            parent_file = Path(tmp) / "not-a-directory"
            parent_file.write_text("x", encoding="utf-8")
            adapter = CountingAdapter()
            gateway = ConnectorGateway(
                telemetry=ConnectorTelemetry(parent_file / "connectors.jsonl")
            )
            gateway._adapters["local.mock"] = adapter
            with self.assertRaisesRegex(ConnectorError, "appel bloqué"):
                gateway.generate(
                    "local.mock",
                    GenerationRequest("demo", "text", "prompt"),
                    {"connectors.generate"},
                )
            self.assertEqual(adapter.calls, 0)

    def test_failed_terminal_write_leaves_reconcilable_incomplete_operation(self):
        class FailOnSecondRecord(ConnectorTelemetry):
            def __init__(self, path):
                super().__init__(path)
                self.calls = 0

            def record(self, action, provider_id, details):
                self.calls += 1
                if self.calls == 2:
                    raise ConnectorTelemetryError("simulated write failure")
                return super().record(action, provider_id, details)

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            gateway = ConnectorGateway(telemetry=FailOnSecondRecord(ledger))
            with self.assertRaisesRegex(ConnectorError, "réconciliation requise"):
                gateway.generate(
                    "local.mock",
                    GenerationRequest("demo", "text", "prompt"),
                    {"connectors.generate"},
                )
            report = build_connector_usage_report(ledger)
            self.assertEqual(report["totals"]["calls_started"], 1)
            self.assertEqual(report["totals"]["calls_incomplete"], 1)

    def test_telemetry_rejects_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            telemetry = ConnectorTelemetry(Path(tmp) / "connectors.jsonl")
            with self.assertRaises(ConnectorTelemetryError):
                telemetry.record(
                    "connector.call.started",
                    "local.mock",
                    {
                        "operation_id": "0" * 32,
                        "kind": "text",
                        "estimated_cost_xof": 0,
                        "prompt": "must not be accepted",
                    },
                )

    def test_report_rejects_orphan_terminal_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            telemetry = ConnectorTelemetry(ledger)
            telemetry.record(
                "connector.call.completed",
                "local.mock",
                {
                    "operation_id": "1" * 32,
                    "kind": "text",
                    "estimated_cost_xof": 0,
                    "reported_cost_xof": 0,
                    "duration_ms": 1,
                    "simulated": True,
                },
            )
            with self.assertRaises(ConnectorTelemetryError):
                build_connector_usage_report(ledger)

    def test_report_rejects_duplicate_terminal_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            telemetry = ConnectorTelemetry(ledger)
            start = {
                "operation_id": "2" * 32,
                "kind": "image",
                "estimated_cost_xof": 0,
            }
            terminal = {
                **start,
                "reported_cost_xof": 0,
                "duration_ms": 1,
                "simulated": True,
            }
            telemetry.record("connector.call.started", "local.mock", start)
            telemetry.record("connector.call.completed", "local.mock", terminal)
            telemetry.record("connector.call.completed", "local.mock", terminal)
            with self.assertRaises(ConnectorTelemetryError):
                build_connector_usage_report(ledger)

    def test_report_rejects_corrupted_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "connectors.jsonl"
            ledger.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(ConnectorTelemetryError):
                build_connector_usage_report(ledger)


if __name__ == "__main__":
    unittest.main()
