"""PAPI KIDS book-to-image orchestration for PKP-0001.

Parsing and planning are offline. Provider execution is opt-in, free-quota-only,
and requires an explicit zero-spend authorization on every invocation.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .image_campaign import execute_image_campaign, plan_image_campaign
from .image_production_engine import ImageProductionEngine

SCENE_HEADING = re.compile(r"^###\s+(\d{2})\s+[—-]\s+(.+?)\s*$", re.MULTILINE)
EXPECTED_SCENES = 24
BOOK_ID = "PKP-0001"


class PapiKidsOrchestrationError(ValueError):
    """Invalid book source, production plan, quota declaration or execution gate."""


def _read(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise PapiKidsOrchestrationError(f"Source éditoriale inaccessible : {Path(path).name}") from exc


def _scene_sections(markdown: str) -> list[dict[str, Any]]:
    matches = list(SCENE_HEADING.finditer(markdown))
    if len(matches) != EXPECTED_SCENES:
        raise PapiKidsOrchestrationError(
            f"24 scènes attendues dans le brief d'illustration ; {len(matches)} trouvées."
        )
    pages = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if number != index + 1:
            raise PapiKidsOrchestrationError("Les scènes doivent être numérotées de 01 à 24 sans doublon.")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        scene = markdown[match.end():end].strip()
        if not scene:
            raise PapiKidsOrchestrationError(f"Prompt vide pour la scène {number:02d}.")
        pages.append({
            "page_id": f"page-{number:02d}",
            "page_number": number,
            "prompt": scene,
        })
    return pages


def prepare_pkp0001_campaign(
    *,
    prompts_path: str | Path,
    character_bible_path: str | Path,
    model: str,
    model_costs: dict[str, int],
    free_quota_confirmed: bool,
    max_batch_size: int = 4,
    max_batch_units: int = 2_000,
) -> dict[str, Any]:
    """Build a deterministic 24-page plan; no model or network call is made."""
    if free_quota_confirmed is not True:
        raise PapiKidsOrchestrationError("Modèle/quota gratuit non confirmé : plan de production bloqué.")
    if not isinstance(model_costs, dict) or model not in model_costs:
        raise PapiKidsOrchestrationError("Coût en unités de quota absent du registre explicite.")
    character_bible = _read(character_bible_path)
    prompt_document = _read(prompts_path)
    scenes = _scene_sections(prompt_document)
    global_instructions = (
        "DIRECTION ARTISTIQUE ET CONTINUITÉ — PKP-0001\n"
        "Utiliser la bible graphique canonique ci-dessous pour conserver les personnages, "
        "vêtements, accessoires, proportions et décors. La bible est une référence de continuité, "
        "pas une autorisation de publication.\n\n"
        + character_bible.strip()
        + "\n\nCONTRAINTES COMMUNES : illustration jeunesse originale ; aucun texte, "
        "lettre, chiffre, logo, filigrane, signature ou marque dans l'image ; ne pas imiter "
        "un artiste, studio, franchise ou œuvre existante. Respecter strictement la sécurité "
        "des enfants : rester sur un chemin stable, loin de l'eau et des déchets ; seuls les "
        "adultes compétents manipulent les déchets et objets dangereux. Ne jamais suggérer "
        "que l'apparence de l'eau prouve qu'elle est potable.\n\n"
    )
    pages = [
        {**page, "prompt": global_instructions + page["prompt"]}
        for page in scenes
    ]
    campaign = plan_image_campaign(
        campaign_id="PKP-0001-ILLUSTRATIONS-V1",
        books=[{"book_id": BOOK_ID, "pages": pages}],
        model=model,
        model_costs=model_costs,
        max_batch_size=max_batch_size,
        max_batch_units=max_batch_units,
        max_books=1,
        max_total_pages=EXPECTED_SCENES,
    )
    return {
        "schema_version": 1,
        "book_id": BOOK_ID,
        "title": "Nia et la rivière aux mille reflets",
        "page_count": len(pages),
        "character_bible_sha256": __import__("hashlib").sha256(character_bible.encode("utf-8")).hexdigest(),
        "prompt_source_sha256": __import__("hashlib").sha256(prompt_document.encode("utf-8")).hexdigest(),
        "free_quota_confirmed_at_planning": True,
        "model": model,
        "campaign": campaign,
        "human_approval_required": True,
        "generation_executed": False,
    }


def execute_pkp0001_campaign(
    *,
    prepared: dict[str, Any],
    engine: ImageProductionEngine,
    free_quota_confirmed: bool = False,
    generation_authorized: bool = False,
    spend_limit_minor: int = 0,
    max_batches_per_run: int = 1,
    start_batch_index: int = 0,
    blocked_batch_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Explicitly execute a bounded free-quota slice; paid fallback is impossible."""
    if not isinstance(prepared, dict) or prepared.get("book_id") != BOOK_ID:
        raise PapiKidsOrchestrationError("Dossier PKP-0001 invalide.")
    if generation_authorized is not True:
        raise PapiKidsOrchestrationError("Génération non autorisée explicitement.")
    if free_quota_confirmed is not True:
        raise PapiKidsOrchestrationError("Quota gratuit non confirmé au moment de l'exécution.")
    if spend_limit_minor != 0:
        raise PapiKidsOrchestrationError("Le plafond de dépense doit rester strictement à zéro.")
    generator_models = getattr(getattr(engine, "generator", None), "models", None)
    if not isinstance(generator_models, tuple) or not generator_models or any(
        getattr(model, "free_confirmed", False) is not True for model in generator_models
    ):
        raise PapiKidsOrchestrationError(
            "Adaptateur non vérifié comme routeur de modèles explicitement gratuits ; exécution refusée."
        )
    report = execute_image_campaign(
        plan=prepared["campaign"],
        engine=engine,
        max_batches_per_run=max_batches_per_run,
        start_batch_index=start_batch_index,
        blocked_batch_ids=blocked_batch_ids,
    )
    return {
        "book_id": BOOK_ID,
        "execution": report,
        "spend_limit_minor": 0,
        "paid_fallback": False,
        "human_approval_required": True,
    }
