"""Tests d'intégrité du journal d'audit sous concurrence inter-processus."""
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from papi_core.audit import append_event, new_event, read_events


def _append_batch(path_text: str, worker_index: int, count: int) -> None:
    path = Path(path_text)
    for item_index in range(count):
        event = new_event(
            event_id=f"PROCESS-{worker_index:02d}-{item_index:02d}",
            actor=f"worker-{worker_index:02d}",
            action="audit.concurrent_append",
            entity_type="test",
            entity_id=f"batch-{worker_index:02d}",
            details={"sequence": item_index},
        )
        append_event(event, path)


class AuditMultiprocessTests(unittest.TestCase):
    def test_concurrent_processes_preserve_one_valid_chain(self):
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("Le test requiert un système POSIX avec fork.")
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            processes = [
                context.Process(target=_append_batch, args=(str(path), worker, 8))
                for worker in range(4)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=30)
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
                    self.fail("Un processus d'ajout d'audit est resté bloqué.")
                self.assertEqual(process.exitcode, 0)
            events = read_events(path)
            self.assertEqual(len(events), 32)
            self.assertEqual(len({event["event_id"] for event in events}), 32)
            self.assertEqual(len({event["event_hash"] for event in events}), 32)


if __name__ == "__main__":
    unittest.main()
