import unittest
from papi_core.kids_pilot_comparison import KidsPilotComparisonError,compare_pilots,PILOTS

def niche(keyword,index):
    products=[]
    for rank in range(1,11):
        products.append({"rank":rank,"title":f"Book {rank}","asin":f"A{index}{rank:07d}",
            "bsr":10000*rank if rank<=3 else 150000,"reviews":rank*5,"price":"8.99",
            "format":"paperback","source_url":f"https://www.amazon.com/dp/A{index}{rank:07d}",
            "observed_at":"2026-11-15"})
    return {"schema_version":1,"marketplace":"Amazon.com","country":"US","keyword":keyword,
        "language":"en","observed_at":"2026-11-15","search_results_count":1000+index,
        "search_source":"synthetic fixture only","search_url":f"https://www.amazon.com/s?k={index}",
        "products":products}

def portfolio():
    return {"schema_version":1,"observed_at":"2026-11-15","pilots":[
        {"book_id":bid,"concept_title":title,"niche_evidence":niche(f"distinct pilot keyword {i}",i)}
        for i,(bid,title) in enumerate(PILOTS.items(),1)]}

class PilotComparisonTests(unittest.TestCase):
    def test_compares_exactly_five_and_ranks_transparently(self):
        r=compare_pilots(portfolio())
        self.assertEqual(r["pilot_count"],5)
        self.assertEqual(r["ranking_method"].startswith("Nombre de trois heuristiques"),True)
        self.assertEqual(r["ranked_pilots"][0]["signals_passed"],3)
        self.assertFalse(r["automatic_go_authorized"])
    def test_missing_pilot_rejected(self):
        d=portfolio(); d["pilots"].pop()
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)
    def test_duplicate_or_unknown_pilot_rejected(self):
        d=portfolio(); d["pilots"][1]["book_id"]=d["pilots"][0]["book_id"]
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)
    def test_wrong_title_rejected(self):
        d=portfolio(); d["pilots"][0]["concept_title"]="Other"
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)
    def test_same_keyword_market_rejected(self):
        d=portfolio(); d["pilots"][1]["niche_evidence"]["keyword"]=d["pilots"][0]["niche_evidence"]["keyword"]
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)
    def test_bad_evidence_rejected(self):
        d=portfolio(); d["pilots"][0]["niche_evidence"]["products"].pop()
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)
    def test_tie_break_is_deterministic(self):
        r=compare_pilots(portfolio())
        ids=[x["book_id"] for x in r["ranked_pilots"]]
        self.assertEqual(ids,sorted(ids))
    def test_impossible_comparison_date_rejected(self):
        d=portfolio(); d["observed_at"]="2026-02-30"
        with self.assertRaises(KidsPilotComparisonError): compare_pilots(d)

if __name__=="__main__": unittest.main()
