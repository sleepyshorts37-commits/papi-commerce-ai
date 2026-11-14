import unittest

from papi_core.execution_queue import ExecutionQueue, QueueError


class RequestSpy:
    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload, prefer))
        return self.response


class ExecutionQueueValidationTests(unittest.TestCase):
    def test_claim_rejects_lease_outside_supported_bounds_before_network(self):
        store = RequestSpy()
        queue = ExecutionQueue(store)
        for seconds in (14, 901, True, 1.5):
            with self.subTest(seconds=seconds):
                with self.assertRaises(QueueError):
                    queue.claim(worker_id="worker-a", lease_seconds=seconds)
        self.assertEqual(store.calls, [])

    def test_claim_generates_a_fresh_lease_token_for_each_reservation(self):
        store = RequestSpy(response=None)
        queue = ExecutionQueue(store)
        self.assertIsNone(queue.claim(worker_id="worker-a", lease_seconds=30))
        self.assertIsNone(queue.claim(worker_id="worker-a", lease_seconds=30))
        first, second = store.calls
        self.assertEqual(first[1], "rpc/papi_claim_job")
        self.assertNotEqual(first[2]["p_lease_token"], second[2]["p_lease_token"])
        self.assertEqual(first[2]["p_worker_id"], "worker-a")

    def test_fail_rejects_error_codes_that_could_leak_sensitive_text(self):
        store = RequestSpy()
        queue = ExecutionQueue(store)
        for code in ("password=secret", "UPPERCASE", "token:abc", "bad code"):
            with self.subTest(code=code):
                with self.assertRaises(QueueError):
                    queue.fail(job_id="job-a", worker_id="worker-a",
                               lease_token="lease-a", error_code=code)
        self.assertEqual(store.calls, [])

    def test_complete_requires_confirmed_boolean_response(self):
        store = RequestSpy(response=False)
        queue = ExecutionQueue(store)
        self.assertFalse(queue.complete(job_id="job-a", worker_id="worker-a",
                                        lease_token="lease-a", result={"ok": True}))
        self.assertEqual(store.calls[0][1], "rpc/papi_complete_job")


if __name__ == "__main__":
    unittest.main()
