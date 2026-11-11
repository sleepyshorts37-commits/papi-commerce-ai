import json
import tempfile
import unittest
from pathlib import Path
from papi_core.sales import SalesError, build_sales_report, load_sales, validate_sales

def empty_registry():
    return {"project":"PAPI COMMERCE AI","prospects":[],"opportunities":[],"offers":[],"pipeline":[],"interactions":[]}

class SalesTests(unittest.TestCase):
    def test_empty_registry_is_valid(self):
        self.assertEqual(validate_sales(empty_registry()),[])
    def test_opt_out_must_be_respected(self):
        data=empty_registry(); data["prospects"]=[{"id":"prospect-01","name":"Demo","source":"https://example.org","status":"new","opt_out":True}]
        self.assertTrue(any("opted_out" in e for e in validate_sales(data)))
    def test_pipeline_requires_existing_references(self):
        data=empty_registry(); data["pipeline"]=[{"id":"deal-01","prospect_id":"prospect-01","offer_id":"offer-01","status":"lead","amount_xof":10000,"probability_pct":25}]
        errors=validate_sales(data)
        self.assertTrue(any("prospect inconnu" in e for e in errors)); self.assertTrue(any("offre inconnue" in e for e in errors))
    def test_sensitive_fields_are_rejected(self):
        data=empty_registry(); data["prospects"]=[{"id":"prospect-01","name":"Demo","source":"public","status":"new","access_token":"secret"}]
        self.assertTrue(any("sensible" in e for e in validate_sales(data)))
    def test_external_action_requires_approval_and_evidence(self):
        data=empty_registry(); data["prospects"]=[{"id":"prospect-01","name":"Demo","source":"public","status":"new"}]
        data["interactions"]=[{"id":"interaction-01","prospect_id":"prospect-01","type":"sent_verified","external_action":True}]
        errors=validate_sales(data)
        self.assertTrue(any("approbation" in e for e in errors)); self.assertTrue(any("preuve" in e for e in errors))
    def test_report_calculates_margin_and_weighted_pipeline(self):
        data=empty_registry()
        data["prospects"]=[{"id":"prospect-01","name":"Demo","source":"public","status":"qualified"}]
        data["offers"]=[{"id":"offer-01","name":"Service","activity":"PAPI SERVICES","price_xof":10000,"direct_cost_xof":2000,"status":"active"}]
        data["pipeline"]=[{"id":"deal-01","prospect_id":"prospect-01","offer_id":"offer-01","status":"proposal","amount_xof":10000,"probability_pct":50}]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"sales.json"; path.write_text(json.dumps(data),encoding="utf-8"); report=build_sales_report(path)
        self.assertEqual(report["active_offer_margin_xof"],8000)
        self.assertEqual(report["pipeline_weighted_value_xof"],5000)
        self.assertEqual(report["verified_revenue_xof"],0)
        self.assertFalse(report["external_actions_enabled"])
    def test_invalid_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"sales.json"; path.write_text("{broken",encoding="utf-8")
            with self.assertRaises(SalesError): load_sales(path)

if __name__ == "__main__":
    unittest.main()
