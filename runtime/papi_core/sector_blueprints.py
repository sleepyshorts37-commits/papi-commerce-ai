"""Governed content blueprints for sector-specific PAPI WEB BUILDER projects.

Blueprints are planning metadata, not published claims. Values shown as required
facts must be supplied and verified by the business owner before rendering.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class SectorBlueprintError(ValueError):
    """Raised when a requested sector blueprint is unknown or malformed."""


_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "corporate": {
        "label": "Entreprise",
        "audience": "Décideurs, partenaires et clients professionnels",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter clairement l'entreprise et sa proposition de valeur."},
            {"slug": "about", "title": "À propos", "purpose": "Présenter l'équipe, l'histoire et les engagements vérifiables."},
            {"slug": "services", "title": "Services", "purpose": "Décrire les prestations, périmètres et modalités."},
            {"slug": "contact", "title": "Contact", "purpose": "Permettre une prise de contact volontaire."},
        ],
        "required_facts": ["raison sociale", "zone d'intervention", "services réellement proposés", "coordonnées validées"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "about": ["intro", "stats"], "services": ["feature_grid", "faq"]},
        "guardrails": ["Ne pas inventer de références clients, certifications ou résultats."],
    },
    "ecommerce": {
        "label": "Commerce et boutique",
        "audience": "Acheteurs particuliers et professionnels",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter la boutique et les catégories de produits."},
            {"slug": "catalog", "title": "Catalogue", "purpose": "Présenter les produits et leurs caractéristiques vérifiées."},
            {"slug": "delivery", "title": "Livraison et retours", "purpose": "Expliquer les zones, frais, délais et conditions confirmés."},
            {"slug": "contact", "title": "Contact", "purpose": "Présenter les canaux de commande et de support."},
        ],
        "required_facts": ["catalogue réel", "prix et devise", "disponibilité confirmée", "zones et frais de livraison", "conditions de retour"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "catalog": ["feature_grid", "faq"], "delivery": ["intro", "faq"]},
        "guardrails": ["Ne jamais inventer prix, stock, promotions, délais ou garanties.", "Afficher clairement les conditions de retour communiquées par le vendeur."],
    },
    "hospitality": {
        "label": "Hôtellerie et restauration",
        "audience": "Voyageurs, résidents et groupes",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter l'établissement et son expérience."},
            {"slug": "rooms", "title": "Hébergement et espaces", "purpose": "Décrire les chambres, équipements ou espaces réellement disponibles."},
            {"slug": "services", "title": "Services et restauration", "purpose": "Présenter les services, menus et prestations confirmés."},
            {"slug": "contact", "title": "Réservation et contact", "purpose": "Expliquer comment demander une réservation."},
        ],
        "required_facts": ["adresse", "types de chambres ou espaces", "équipements confirmés", "horaires", "tarifs et conditions de réservation"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "rooms": ["feature_grid", "faq"], "services": ["feature_grid"], "contact": ["intro", "faq"]},
        "guardrails": ["Ne pas promettre de disponibilité sans vérification en temps réel.", "Ne pas inventer tarifs, équipements, menus ou avis clients."],
    },
    "professional_services": {
        "label": "Services professionnels",
        "audience": "Clients recherchant une expertise ou un accompagnement",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter le positionnement et les domaines d'intervention."},
            {"slug": "expertise", "title": "Expertises", "purpose": "Décrire les compétences et livrables proposés."},
            {"slug": "process", "title": "Méthode", "purpose": "Expliquer les étapes réelles d'une mission."},
            {"slug": "contact", "title": "Contact", "purpose": "Permettre une demande d'information ou de devis."},
        ],
        "required_facts": ["domaines de compétence", "livrables", "périmètre de mission", "modalités et coordonnées"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "expertise": ["feature_grid", "faq"], "process": ["intro", "stats"]},
        "guardrails": ["Ne pas inventer diplômes, accréditations, références ou garanties de résultat."],
    },
    "education": {
        "label": "Éducation et formation",
        "audience": "Apprenants, parents et organisations",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter l'établissement ou l'offre de formation."},
            {"slug": "programs", "title": "Programmes", "purpose": "Décrire les cours, niveaux et objectifs pédagogiques."},
            {"slug": "admissions", "title": "Inscriptions", "purpose": "Expliquer les conditions, pièces et étapes d'inscription."},
            {"slug": "contact", "title": "Contact", "purpose": "Présenter les coordonnées et horaires d'accueil."},
        ],
        "required_facts": ["programmes actifs", "niveaux", "calendrier", "conditions et frais d'inscription", "statut d'accréditation si revendiqué"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "programs": ["feature_grid", "faq"], "admissions": ["intro", "faq"]},
        "guardrails": ["Ne pas inventer diplômes reconnus, accréditations, taux de réussite ou débouchés garantis."],
    },
    "health": {
        "label": "Santé et bien-être",
        "audience": "Patients et personnes recherchant des informations de santé",
        "pages": [
            {"slug": "home", "title": "Accueil", "purpose": "Présenter la structure et ses services autorisés."},
            {"slug": "services", "title": "Services", "purpose": "Décrire les services, professionnels et modalités d'accueil."},
            {"slug": "practical-info", "title": "Informations pratiques", "purpose": "Présenter horaires, accès et modalités de rendez-vous."},
            {"slug": "contact", "title": "Contact", "purpose": "Fournir les coordonnées et les consignes de contact."},
        ],
        "required_facts": ["statut et autorisations", "professionnels et qualifications vérifiés", "services réellement fournis", "horaires et coordonnées"],
        "recommended_sections": {"home": ["intro", "feature_grid", "cta"], "services": ["feature_grid", "faq"], "practical-info": ["intro", "faq"]},
        "guardrails": ["Aucune promesse de guérison, efficacité ou résultat garanti.", "Aucun diagnostic, posologie ou conseil médical personnalisé.", "Ne publier aucune qualification ou autorisation non vérifiée."],
    },
}


def list_sector_blueprints() -> list[dict[str, str]]:
    """Return stable identifiers and labels without exposing mutable internals."""
    return [{"industry": key, "label": value["label"]} for key, value in _BLUEPRINTS.items()]


def get_sector_blueprint(industry: str) -> dict[str, Any]:
    """Return a defensive copy of the sector page plan and its content safeguards."""
    if not isinstance(industry, str) or industry not in _BLUEPRINTS:
        raise SectorBlueprintError("Secteur non pris en charge.")
    return {"industry": industry, **deepcopy(_BLUEPRINTS[industry])}


def validate_sector_facts(industry: str, facts: Any) -> dict[str, Any]:
    """Check that all mandatory fact labels are supplied; does not verify truth."""
    blueprint = get_sector_blueprint(industry)
    if not isinstance(facts, dict):
        raise SectorBlueprintError("Les faits doivent être fournis sous forme d'objet.")
    required = blueprint["required_facts"]
    missing = [label for label in required if not isinstance(facts.get(label), str) or not facts[label].strip()]
    return {
        "industry": industry,
        "complete": not missing,
        "missing_facts": missing,
        "human_verification_required": True,
        "truth_verified": False,
        "guardrails": blueprint["guardrails"],
    }
