import unittest

from papi_core.papi_kids_kdp_metadata import (
    KDPListingMetadataError,
    is_valid_isbn13,
    validate_kdp_listing_metadata,
)


def valid_metadata():
    return {
        "title": "Nia et la rivière aux mille reflets",
        "author": "Auteur confirmé",
        "description": "Une histoire illustrée pour découvrir la rivière et protéger la nature en famille.",
        "language": "fr",
        "keywords": ["album jeunesse", "rivière", "nature"],
        "categories": ["Children's Books / Environment", "Children's Books / Social Themes"],
        "reading_age_min": 5, "reading_age_max": 8,
        "commercial_use_confirmed": True,
        "rights_holder": "Auteur confirmé", "rights_evidence_ref": "rights-doc-01",
        "territories": "worldwide",
        "isbn_strategy": "kdp_free_isbn",
        "marketplace": "Amazon.fr", "currency": "EUR", "list_price": 12.99,
        "pricing_verified": True, "pricing_verified_at": "2026-11-15",
    }


class KDPListingMetadataTests(unittest.TestCase):
    def test_complete_listing_is_ready_only_for_owner_review(self):
        result = validate_kdp_listing_metadata(valid_metadata())
        self.assertEqual(result["status"], "ready_for_owner_review")
        self.assertEqual(result["blocker_count"], 0)
        self.assertTrue(result["owner_review_required"])
        self.assertFalse(result["kdp_upload_ready"])

    def test_missing_author_categories_rights_and_isbn_are_blockers(self):
        metadata = valid_metadata()
        for field in ("author", "categories", "rights_holder", "rights_evidence_ref", "isbn_strategy"):
            metadata.pop(field)
        result = validate_kdp_listing_metadata(metadata)
        self.assertEqual(result["status"], "incomplete")
        self.assertGreaterEqual(result["blocker_count"], 5)

    def test_limits_keywords_categories_and_reading_age(self):
        metadata = valid_metadata()
        metadata["keywords"] = ["mot"] * 8
        metadata["categories"] = ["une", "deux", "trois", "quatre"]
        metadata["reading_age_min"] = 9
        metadata["reading_age_max"] = 5
        result = validate_kdp_listing_metadata(metadata)
        self.assertEqual(result["blocker_count"], 3)

    def test_isbn13_checksum_and_own_isbn_publisher_requirement(self):
        self.assertTrue(is_valid_isbn13("978-2-07-036822-8"))
        self.assertFalse(is_valid_isbn13("9782070368229"))
        metadata = valid_metadata()
        metadata["isbn_strategy"] = "own_isbn"
        metadata["isbn"] = "9782070368228"
        metadata.pop("publisher")
        result = validate_kdp_listing_metadata(metadata)
        self.assertTrue(any("Éditeur déclaré" in item for item in result["blockers"]))

    def test_ebook_does_not_accept_print_isbn(self):
        metadata = valid_metadata()
        metadata["isbn"] = "9782070368228"
        result = validate_kdp_listing_metadata(metadata, paperback=False)
        self.assertTrue(any("ISBN imprimé" in item for item in result["blockers"]))

    def test_short_description_and_non_finite_price_are_rejected(self):
        metadata = valid_metadata()
        metadata["description"] = "Trop court."
        metadata["list_price"] = float("nan")
        result = validate_kdp_listing_metadata(metadata)
        self.assertTrue(any("Description" in item for item in result["blockers"]))
        self.assertTrue(any("Prix catalogue" in item for item in result["blockers"]))

    def test_invalid_metadata_type_is_rejected(self):
        with self.assertRaises(KDPListingMetadataError):
            validate_kdp_listing_metadata(None)


if __name__ == "__main__":
    unittest.main()
