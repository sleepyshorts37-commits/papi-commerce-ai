import unittest

from papi_core.workers_report import WorkersReportError, build_workers_report


class WorkersReportTests(unittest.TestCase):
    def test_empty_report_is_safe_and_explicit(self):
        report = build_workers_report()
        self.assertEqual(report["platforms"]["total"], 0)
        self.assertEqual(report["human_handoffs"]["awaiting_user_count"], 0)
        self.assertFalse(report["governance"]["external_actions_performed"])

    def test_combines_platform_handoff_and_profitability_states(self):
        report = build_workers_report(
            platform_candidates=[
                {"platform_id": "a", "name": "A", "url": "https://a.example",
                 "status": "human_registration_required"},
                {"platform_id": "b", "name": "B", "url": "https://b.example",
                 "status": "rejected"},
            ],
            handoffs=[
                {"handoff_id": "H1", "platform_name": "A",
                 "official_url": "https://a.example", "required_user_action": "Créer le compte",
                 "status": "awaiting_user"},
                {"handoff_id": "H2", "status": "resumed"},
            ],
            profitability_results=[
                {"offer_id": "O1", "currency": "XOF",
                 "estimated_net_profit_after_labor": "5000.00",
                 "estimated_net_hourly_rate": "1000.00",
                 "estimated_net_margin_percent": "20.00",
                 "status": "viable_for_human_review"},
                {"offer_id": "O2", "status": "loss_making"},
            ],
        )
        self.assertEqual(report["platforms"]["by_status"]["human_registration_required"], 1)
        self.assertEqual(report["human_handoffs"]["awaiting_user_count"], 1)
        self.assertEqual(report["human_handoffs"]["user_actions"][0]["handoff_id"], "H1")
        self.assertEqual(report["profitability"]["by_status"]["viable_for_human_review"], 1)
        self.assertEqual(report["profitability"]["offers_for_human_review"][0]["offer_id"], "O1")

    def test_only_waiting_handoffs_are_user_action_items(self):
        report = build_workers_report(handoffs=[
            {"handoff_id": "A", "status": "awaiting_user"},
            {"handoff_id": "B", "status": "user_confirmed"},
            {"handoff_id": "C", "status": "completed"},
        ])
        self.assertEqual([x["handoff_id"] for x in report["human_handoffs"]["user_actions"]], ["A"])

    def test_invalid_collections_are_rejected(self):
        with self.assertRaises(WorkersReportError):
            build_workers_report(platform_candidates={"bad": "shape"})
        with self.assertRaises(WorkersReportError):
            build_workers_report(handoffs=["not-an-object"])

    def test_report_never_claims_live_actions(self):
        report = build_workers_report(
            platform_candidates=[{"status": "verified_ready"}],
            handoffs=[{"status": "completed"}],
            profitability_results=[{"status": "viable_for_human_review"}],
        )
        governance = report["governance"]
        self.assertFalse(governance["live_search_performed"])
        self.assertFalse(governance["notifications_sent"])
        self.assertFalse(governance["spending_authorized"])
        self.assertFalse(governance["contracts_accepted"])
        self.assertFalse(governance["external_actions_performed"])


if __name__ == "__main__":
    unittest.main()
