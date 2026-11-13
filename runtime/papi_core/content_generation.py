"""Deterministic, fact-grounded commercial content generation for PAPI."""
from __future__ import annotations
import re
from typing import Any

CONTENT_TYPES = {"product", "service", "business_page", "social_post"}
SECTORS = {"pharmacy", "hotel", "restaurant", "retail", "professional_services"}
TONES = {"professional", "friendly", "premium", "concise"}
MAX_FACTS = 8
MAX_OUTPUT_CHARS = 5000
_UNSUPPORTED_CLAIMS = re.compile(
    r"\b(?:gu[eé]rit|soigne\s+(?:le|la|les|un|une)|garanti(?:e|s|es)?|"
    r"sans\s+aucun\s+risque|r[eé]sultat(?:s)?\s+garanti(?:s)?|"
    r"100\s*%\s+(?:efficace|s[uû]r|garanti))\b", re.IGNORECASE
)
_DOSAGE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|mL)\b", re.IGNORECASE)

class ContentGenerationError(ValueError):
    """Invalid or unsafe commercial content brief."""

_SECTOR_LABELS = {
    "pharmacy": "Pharmacie", "hotel": "Hôtel", "restaurant": "Restaurant",
    "retail": "Boutique", "professional_services": "Services professionnels",
}
_KIND_LABELS = {
    "product": "Fiche produit", "service": "Présentation de service",
    "business_page": "Présentation de l’établissement", "social_post": "Publication commerciale",
}
_TONE_OPENERS = {
    "professional": "Découvrez", "friendly": "Bienvenue dans l’univers de",
    "premium": "L’exigence et l’attention au détail autour de", "concise": "À découvrir :",
}
_SECTOR_CONTEXT = {
    "pharmacy": "Pour toute question de santé, demandez conseil à un professionnel de santé.",
    "hotel": "Les disponibilités, tarifs et conditions sont à confirmer auprès de l’établissement.",
    "restaurant": "Les ingrédients et allergènes sont à confirmer directement auprès de l’établissement.",
    "retail": "Vérifiez les caractéristiques, le prix et la disponibilité avant votre achat.",
    "professional_services": "Le périmètre, les délais et les conditions sont à confirmer dans un devis.",
}

def _clean(value: Any, field: str, limit: int = 180) -> str:
    if not isinstance(value, str):
        raise ContentGenerationError(f"{field}: texte attendu.")
    value = " ".join(value.split()).strip()
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        raise ContentGenerationError(f"{field}: longueur ou caractères invalides.")
    if "<" in value or ">" in value:
        raise ContentGenerationError(f"{field}: balisage non autorisé.")
    return value

def _validate_brief(brief: Any) -> dict[str, Any]:
    allowed = {"content_type", "sector", "brand", "offer", "audience", "facts", "tone", "cta"}
    if not isinstance(brief, dict) or set(brief) - allowed:
        raise ContentGenerationError("Brief invalide : champs inconnus ou format incorrect.")
    required = {"content_type", "sector", "brand", "offer", "facts"}
    if not required.issubset(brief):
        raise ContentGenerationError("Brief incomplet : content_type, sector, brand, offer et facts sont requis.")
    content_type, sector, tone = brief["content_type"], brief["sector"], brief.get("tone", "professional")
    if not all(isinstance(value, str) for value in (content_type, sector, tone)):
        raise ContentGenerationError("content_type, sector et tone doivent être des textes.")
    if content_type not in CONTENT_TYPES:
        raise ContentGenerationError("Type de contenu non pris en charge.")
    if sector not in SECTORS:
        raise ContentGenerationError("Secteur non pris en charge.")
    if tone not in TONES:
        raise ContentGenerationError("Ton non pris en charge.")
    brand = _clean(brief["brand"], "brand", 100)
    offer = _clean(brief["offer"], "offer", 180)
    audience = _clean(brief.get("audience", "notre clientèle"), "audience", 100)
    cta = _clean(brief.get("cta", "Contactez-nous pour en savoir plus."), "cta", 120)
    facts = brief["facts"]
    if not isinstance(facts, list) or not 1 <= len(facts) <= MAX_FACTS:
        raise ContentGenerationError(f"facts doit contenir entre 1 et {MAX_FACTS} éléments.")
    clean_facts = [_clean(item, f"facts[{i}]", 180) for i, item in enumerate(facts)]
    source = " ".join([brand, offer, audience, cta, *clean_facts])
    if _UNSUPPORTED_CLAIMS.search(source):
        raise ContentGenerationError("Allégation de résultat ou d’efficacité non vérifiée : validation humaine requise.")
    if sector == "pharmacy" and _DOSAGE.search(source):
        raise ContentGenerationError("Les dosages et posologies ne sont pas générés par cet outil.")
    return {"content_type": content_type, "sector": sector, "brand": brand,
            "offer": offer, "audience": audience, "facts": clean_facts, "tone": tone, "cta": cta}

def generate_commercial_content(brief: dict[str, Any]) -> dict[str, str]:
    """Build a structured draft exclusively from validated brief fields."""
    data = _validate_brief(brief)
    kind, sector = data["content_type"], data["sector"]
    brand, offer, facts = data["brand"], data["offer"], data["facts"]
    intro = f"{_TONE_OPENERS[data['tone']]} {offer.lower()} chez {brand}, pensé pour {data['audience']}."
    fact_lines = "\n".join(f"• {fact}" for fact in facts)
    if kind == "product":
        body = f"{intro}\n\nÀ retenir :\n{fact_lines}"
    elif kind == "service":
        body = f"{intro}\n\nNotre présentation :\n{fact_lines}"
    elif kind == "business_page":
        body = f"{brand} — {_SECTOR_LABELS[sector]}.\n\n{intro}\n\nNotre établissement :\n{fact_lines}"
    else:
        body = f"{intro}\n\n{fact_lines}\n\n{data['cta']}"
    result = {
        "content_type": kind, "sector": sector, "title": f"{offer} | {brand}",
        "body": body, "cta": "" if kind == "social_post" else data["cta"],
        "disclaimer": _SECTOR_CONTEXT[sector], "review_required": "true",
        "source_policy": "Faits fournis uniquement ; vérification humaine avant diffusion.",
    }
    if sum(len(value) for value in result.values()) > MAX_OUTPUT_CHARS:
        raise ContentGenerationError("Le contenu généré dépasse la limite autorisée.")
    return result
