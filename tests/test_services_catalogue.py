import unittest
from runtime.papi_core.services_catalogue import list_services, preview_quote

class ServicesCatalogueTests(unittest.TestCase):
    def test_only_proposed_services_by_default(self):
        items=list_services()
        self.assertEqual({x["service_code"] for x in items},
                         {"WHATSAPP_ASSISTANT_BASIC","WHATSAPP_PHARMACY_ASSISTANT"})
    def test_drafts_can_be_listed_explicitly(self):
        self.assertEqual(len(list_services(include_draft=True)),5)
    def test_basic_monthly_preview(self):
        q=preview_quote("WHATSAPP_ASSISTANT_BASIC",months=3)
        self.assertEqual(q["total_preview_xof"],30000)
        self.assertFalse(q["binding_offer"])
    def test_pharmacy_setup_and_monthly(self):
        q=preview_quote("WHATSAPP_PHARMACY_ASSISTANT",months=2)
        self.assertEqual(q["total_preview_xof"],80000)
    def test_custom_price_preview(self):
        q=preview_quote("WHATSAPP_ASSISTANT_BASIC",months=2,custom_setup_xof=5000,custom_monthly_xof=12000)
        self.assertEqual(q["total_preview_xof"],29000)
    def test_draft_service_cannot_be_quoted(self):
        with self.assertRaises(ValueError):
            preview_quote("PROSPECT_RESEARCH")
    def test_unknown_service_rejected(self):
        with self.assertRaises(ValueError):
            preview_quote("UNKNOWN")
    def test_invalid_months_rejected(self):
        with self.assertRaises(ValueError):
            preview_quote("WHATSAPP_ASSISTANT_BASIC",months=0)
    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            preview_quote("WHATSAPP_ASSISTANT_BASIC",custom_monthly_xof=-1)
    def test_zero_cost_and_no_external_action(self):
        q=preview_quote("WHATSAPP_ASSISTANT_BASIC")
        self.assertEqual(q["setup_xof"],0)
        self.assertTrue(q["requires_human_approval"])

if __name__=="__main__": unittest.main()
