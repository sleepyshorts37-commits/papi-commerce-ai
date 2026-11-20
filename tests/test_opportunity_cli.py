import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from papi_core.__main__ import main


class OpportunityCliTests(unittest.TestCase):
    def test_opportunity_rank_command_emits_read_only_xof_ranking(self):
        sample = [{
            "id": "cli-option",
            "activity": "PAPI SERVICES",
            "price_xof": 10000,
            "direct_cost_xof": 1000,
            "delivery_cost_xof": 0,
            "commission_pct": 0,
            "payment_fee_xof": 0,
            "refund_reserve_pct": 0,
            "initial_cost_xof": 0,
            "customer_advance_xof": 0,
            "supplier_payment_days": 0,
            "customer_payment_days": 0,
            "first_revenue_days": 2,
            "risk_pct": 10,
            "confidence_pct": 90
        }]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "opportunities.json"
            source.write_text(json.dumps(sample), encoding="utf-8")
            output = StringIO()
            with patch("sys.argv", ["papi_core", "opportunity-rank", str(source)]):
                with redirect_stdout(output):
                    status = main()
        result = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(result["currency"], "XOF")
        self.assertEqual(result["ranked"][0]["id"], "cli-option")
        self.assertFalse(result["ranked"][0]["external_action_enabled"])


if __name__ == "__main__":
    unittest.main()
