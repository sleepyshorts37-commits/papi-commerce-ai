import unittest
from papi_core.kids_niche_research import KidsNicheError,assess_niche

def fixture(results=1200,bsrs=(50000,70000,90000),reviews=(10,20,30,40,50,10,20,30,40,50)):
    products=[]
    for i,(bsr,review) in enumerate(zip([*bsrs,*([120000]*7)],reviews),1):
        products.append({"rank":i,"title":f"Test book {i}","asin":f"ASIN{i:06d}","bsr":bsr,"reviews":review,"price":"9.99","format":"paperback","source_url":f"https://www.amazon.com/dp/ASIN{i:06d}","observed_at":"2026-11-15"})
    return {"schema_version":1,"marketplace":"Amazon.com","country":"US","keyword":"kids activity book ages 5-7","language":"en","observed_at":"2026-11-15","search_results_count":results,"search_source":"manual test fixture, not market evidence","search_url":"https://www.amazon.com/s?k=fixture","products":products}

class KidsNicheResearchTests(unittest.TestCase):
    def test_all_three_heuristics_pass_but_no_automatic_go(self):
        r=assess_niche(fixture())
        self.assertEqual(r["signals_passed"],3)
        self.assertEqual(r["screening_result"],"PROMISING_FOR_HUMAN_REVIEW")
        self.assertEqual(r["decision"],"HUMAN_REVIEW_REQUIRED")
        self.assertFalse(r["automatic_go_authorized"])
    def test_competition_threshold_is_strict(self):
        r=assess_niche(fixture(results=2500))
        self.assertFalse(r["criteria"]["competition_below_2500_results"])
    def test_top_three_bsr_threshold_is_strict(self):
        r=assess_niche(fixture(bsrs=(100000,70000,90000)))
        self.assertFalse(r["criteria"]["top_three_bsr_below_100000"])
    def test_average_review_threshold_is_strict(self):
        r=assess_niche(fixture(reviews=(50,50,50,50,50,50,50,50,50,50)))
        self.assertFalse(r["criteria"]["first_page_average_reviews_below_50"])
    def test_fewer_than_ten_products_rejected(self):
        d=fixture(); d["products"]=d["products"][:9]
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_duplicate_asin_rejected(self):
        d=fixture(); d["products"][1]["asin"]=d["products"][0]["asin"]
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_impossible_date_rejected(self):
        d=fixture(); d["observed_at"]="2026-02-30"
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_bsr_zero_rejected(self):
        d=fixture(); d["products"][0]["bsr"]=0
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_invalid_rank_sequence_rejected(self):
        d=fixture(); d["products"][0]["rank"]=2
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_boolean_integer_rejected(self):
        d=fixture(); d["products"][0]["reviews"]=True
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_missing_evidence_rejected(self):
        d=fixture(); d["products"][0]["source_url"]=""
        with self.assertRaises(KidsNicheError): assess_niche(d)
    def test_weak_signals_not_go(self):
        r=assess_niche(fixture(results=9000,bsrs=(200000,300000,400000)))
        self.assertEqual(r["screening_result"],"WEAK_SIGNAL_STOP_OR_REPOSITION")
        self.assertFalse(r["publication_authorized"])

if __name__=="__main__": unittest.main()
