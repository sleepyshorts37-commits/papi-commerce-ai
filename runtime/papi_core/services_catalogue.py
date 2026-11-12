"""Curated PAPI SERVICES catalogue and deterministic quote previews.

Prices are proposed catalogue values, not binding offers. No quote is sent and no
service is purchased or activated by this module.
"""
from __future__ import annotations
from typing import Any

CATALOGUE = {
    "WHATSAPP_ASSISTANT_BASIC": {
        "name": "Assistant WhatsApp général",
        "description": "Réponses aux questions fréquentes, qualification des demandes et orientation vers un opérateur.",
        "setup_xof": 0, "monthly_xof": 10000, "billing": "monthly",
        "status": "proposed", "requires_human_validation": True,
        "limitations": ["Connexion WhatsApp et automatisations à valider séparément", "Aucune promesse de disponibilité 24/7 avant déploiement et tests"],
    },
    "WHATSAPP_PHARMACY_ASSISTANT": {
        "name": "Assistant WhatsApp pharmacie",
        "description": "Catalogue informatif, demandes de disponibilité et coordination humaine des livraisons.",
        "setup_xof": 50000, "monthly_xof": 15000, "billing": "setup_plus_monthly",
        "status": "proposed", "requires_human_validation": True,
        "limitations": ["Aucune recommandation médicale autonome", "Validation pharmacien obligatoire", "Stock et livraison non confirmés automatiquement"],
    },
    "CUSTOMER_SUPPORT_STARTER": {
        "name": "Support client externalisé – formule démarrage",
        "description": "Tri des demandes, réponses préparées et rapport de suivi pour petite entreprise.",
        "setup_xof": 0, "monthly_xof": 25000, "billing": "monthly",
        "status": "draft", "requires_human_validation": True,
        "limitations": ["Volume et horaires à convenir", "Canaux et accès fournis par le client après accord"],
    },
    "PROSPECT_RESEARCH": {
        "name": "Recherche de prospects B2B",
        "description": "Recherche sur sources publiques, qualification et remise d'une liste professionnelle.",
        "setup_xof": 0, "monthly_xof": 0, "billing": "custom_quote",
        "status": "draft", "requires_human_validation": True,
        "limitations": ["Périmètre, volume et tarif sur devis", "Respect des règles de confidentialité et anti-spam"],
    },
    "ADMIN_DATA_ENTRY": {
        "name": "Saisie et organisation administrative",
        "description": "Mise en forme de tableaux, classement de données non sensibles et rapports simples.",
        "setup_xof": 0, "monthly_xof": 0, "billing": "custom_quote",
        "status": "draft", "requires_human_validation": True,
        "limitations": ["Documents et données minimisés", "Périmètre et tarif sur devis"],
    },
}

def list_services(*, include_draft: bool = False) -> list[dict[str, Any]]:
    """Return proposed catalogue entries; drafts are hidden unless explicitly requested."""
    if not isinstance(include_draft, bool):
        raise ValueError("include_draft doit être booléen.")
    result=[]
    for code,item in CATALOGUE.items():
        if item["status"]=="draft" and not include_draft:
            continue
        result.append({"service_code":code,**item})
    return result

def preview_quote(service_code: str, *, months: int = 1, custom_setup_xof: int | None = None,
                  custom_monthly_xof: int | None = None) -> dict[str, Any]:
    """Calculate a non-binding price preview; never creates or sends a real quote."""
    if not isinstance(service_code,str) or service_code not in CATALOGUE:
        raise ValueError("Service inconnu.")
    if isinstance(months,bool) or not isinstance(months,int) or not 1<=months<=36:
        raise ValueError("months doit être compris entre 1 et 36.")
    item=CATALOGUE[service_code]
    if item["status"]!="proposed":
        raise ValueError("Ce service est en brouillon et nécessite une validation commerciale.")
    setup=item["setup_xof"] if custom_setup_xof is None else custom_setup_xof
    monthly=item["monthly_xof"] if custom_monthly_xof is None else custom_monthly_xof
    for value in (setup,monthly):
        if isinstance(value,bool) or not isinstance(value,int) or value<0:
            raise ValueError("Les montants doivent être des entiers XOF positifs ou nuls.")
    return {"service_code":service_code,"service_name":item["name"],
            "setup_xof":setup,"monthly_xof":monthly,"months":months,
            "total_preview_xof":setup+monthly*months,"currency":"XOF",
            "binding_offer":False,"status":"draft_preview",
            "requires_human_approval":True,
            "note":"Prix indicatif à valider selon le besoin, les coûts réels, les capacités et les conditions convenues."}
