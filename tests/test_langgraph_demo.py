import importlib.util
import unittest

from papi_core.langgraph_demo import build_readonly_demo_graph


LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "LangGraph optionnel non installé")
class LangGraphDemoTests(unittest.TestCase):
    def test_preview_is_called_and_result_is_returned(self):
        calls = []

        def preview(request):
            calls.append(request)
            return {"mode": "preview", "request_length": len(request)}

        graph = build_readonly_demo_graph(preview)
        result = graph.invoke({"request": "examiner les tâches"})

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["mode"], "preview")
        self.assertEqual(calls, ["examiner les tâches"])

    def test_invalid_request_is_blocked_without_calling_preview(self):
        calls = []
        graph = build_readonly_demo_graph(lambda request: calls.append(request) or {})
        result = graph.invoke({"request": " "})

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["error_code"], "invalid_request")
        self.assertEqual(calls, [])

    def test_checkpointed_thread_supports_retry_with_explicit_history(self):
        from langgraph.checkpoint.memory import InMemorySaver

        attempts = {"count": 0}

        def flaky_preview(request):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("synthetic failure")
            return {"request": request}

        graph = build_readonly_demo_graph(flaky_preview, checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "synthetic-thread"}}

        first = graph.invoke({"request": "premier essai"}, config=config)
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["error_code"], "preview_error")

        second = graph.invoke(
            {"request": "reprise", "history": first["history"]}, config=config
        )
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["history"], ["premier essai", "reprise"])
        self.assertEqual(attempts["count"], 2)

    def test_non_dict_preview_result_is_rejected(self):
        graph = build_readonly_demo_graph(lambda request: ["not", "an", "object"])
        result = graph.invoke({"request": "test"})

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "invalid_preview_result")


if __name__ == "__main__":
    unittest.main()
