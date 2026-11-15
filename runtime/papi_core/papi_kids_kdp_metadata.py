"""Validate Amazon KDP listing metadata without inventing missing author inputs."""
from __future__ import annotations

import re
from typing import Any


class KDPListingMetadataError(ValueError):
    """Invalid or incomplete KDP listing metadata."""


def is_valid_isbn13(value: str) -> bool:
    digits = re.sub(r"[- ]", "", value) if isinstance(value, str) else ""
    if not re.fullmatch(r"\d{13}", digits):
        return False
    total = sum(int(digit) * (1 if index % 2 == 0 else 3) for index, digit in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == int(digits[12])


def validate_kdp_listing_metadata(
    metadata: dict[str, Any],
    *,
    paperback: bool = True,
) -> dict[str, Any]:
    """Return blockers and a normalized draft; ready status still requires owner review."""
    if not isinstance(metadata, dict):
        raise KDPListingMetadataError("Métadonnées KDP absentes ou invalides.")
    blockers = []
    normalized: dict[str, Any] = {}

    def required_text(field: str, label: str, maximum: int) -> None:
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
            blockers.append(f"{label} absent ou hors limite.")
        else:
            normalized[field] = value.strip()

    required_text("title", "Titre", 200)
    required_text("author", "Auteur", 100)
    required_text("description", "Description", 4000)
    language = metadata.get("language")
    if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", language):
        blockers.append("Code de langue invalide.")
    else:
        normalized["language"] = language

    keywords = metadata.get("keywords")
    if (not isinstance(keywords, list) or not 1 <= len(keywords) <= 7
            or any(not isinstance(item, str) or not item.strip() for item in keywords)):
        blockers.append("Entre 1 et 7 mots-clés non vides sont requis.")
    else:
        normalized["keywords"] = [item.strip() for item in keywords]

    categories = metadata.get("categories")
    if (not isinstance(categories, list) or not 1 <= len(categories) <= 3
            or any(not isinstance(item, str) or not item.strip() for item in categories)):
        blockers.append("Entre 1 et 3 catégories KDP doivent être confirmées.")
    else:
        normalized["categories"] = [item.strip() for item in categories]

    age_min = metadata.get("reading_age_min")
    age_max = metadata.get("reading_age_max")
    if (not isinstance(age_min, int) or isinstance(age_min, bool)
            or not isinstance(age_max, int) or isinstance(age_max, bool)
            or not 3 <= age_min <= age_max <= 18):
        blockers.append("Tranche d'âge de lecture invalide ou non confirmée.")
    else:
        normalized["reading_age_min"] = age_min
        normalized["reading_age_max"] = age_max

    if metadata.get("commercial_use_confirmed") is not True:
        blockers.append("Droits d'exploitation commerciale non confirmés.")
    else:
        normalized["commercial_use_confirmed"] = True
    required_text("rights_holder", "Titulaire des droits", 160)
    required_text("rights_evidence_ref", "Preuve des droits", 240)

    territories = metadata.get("territories")
    if territories == "worldwide":
        normalized["territories"] = "worldwide"
    elif (isinstance(territories, list) and territories
          and all(isinstance(item, str) and re.fullmatch(r"[A-Z]{2}", item) for item in territories)):
        normalized["territories"] = sorted(set(territories))
    else:
        blockers.append("Droits territoriaux KDP non confirmés.")

    if paperback:
        strategy = metadata.get("isbn_strategy")
        if strategy == "kdp_free_isbn":
            if metadata.get("isbn"):
                blockers.append("Ne pas fournir d'ISBN personnel avec l'option ISBN gratuit KDP.")
            else:
                normalized["isbn_strategy"] = strategy
        elif strategy == "own_isbn":
            isbn = metadata.get("isbn")
            if not isinstance(isbn, str) or not is_valid_isbn13(isbn):
                blockers.append("ISBN-13 personnel invalide ou absent.")
            else:
                normalized["isbn_strategy"] = strategy
                normalized["isbn"] = re.sub(r"[- ]", "", isbn)
            publisher = metadata.get("publisher")
            if not isinstance(publisher, str) or not publisher.strip():
                blockers.append("Éditeur déclaré requis avec un ISBN personnel.")
            else:
                normalized["publisher"] = publisher.strip()
        else:
            blockers.append("Stratégie ISBN du livre broché non choisie.")
    else:
        if metadata.get("isbn"):
            blockers.append("Un ISBN imprimé ne doit pas être ajouté au dossier ebook par défaut.")

    marketplace = metadata.get("marketplace")
    currency = metadata.get("currency")
    if not isinstance(marketplace, str) or not marketplace.strip():
        blockers.append("Marketplace de vente non confirmé.")
    else:
        normalized["marketplace"] = marketplace.strip()
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        blockers.append("Devise de vente invalide.")
    else:
        normalized["currency"] = currency
    price = metadata.get("list_price")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
        blockers.append("Prix catalogue non confirmé.")
    else:
        normalized["list_price"] = float(price)

    if metadata.get("pricing_verified") is not True or not metadata.get("pricing_verified_at"):
        blockers.append("Prix et redevance non vérifiés avec date.")
    else:
        normalized["pricing_verified"] = True
        normalized["pricing_verified_at"] = metadata["pricing_verified_at"]

    return {
        "status": "ready_for_owner_review" if not blockers else "incomplete",
        "blockers": blockers,
        "blocker_count": len(blockers),
        "normalized_draft": normalized,
        "owner_review_required": True,
        "kdp_upload_ready": False,
        "publication_performed": False,
    }
