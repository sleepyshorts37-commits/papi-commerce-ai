"""PAPI KIDS book-to-image orchestration for PKP-0001.

Parsing and planning are offline. Provider execution is opt-in, free-quota-only,
and requires an explicit zero-spend authorization on every invocation.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
from typing import Any

from .image_campaign import execute_image_campaign, plan_image_campaign
from .image_production_engine import ImageProductionEngine
from .image_quota_evidence import validate_quota_evidence, QuotaEvidenceError

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
    account_ref: str,
    quota_evidence: dict[str, Any],
    max_batch_size: int = 4,
    max_batch_units: int = 2_000,
) -> dict[str, Any]:
    """Build a deterministic 24-page plan; no model or network call is made."""
    if not isinstance(model_costs, dict) or model not in model_costs:
        raise PapiKidsOrchestrationError("Coût en unités de quota absent du registre explicite.")
    try:
        quota_record = validate_quota_evidence(
            quota_evidence, provider="cloudflare",
            account_ref=account_ref,
            model_id=model, estimated_units_per_image=model_costs[model],
            required_images=EXPECTED_SCENES,
        )
    except QuotaEvidenceError as exc:
        raise PapiKidsOrchestrationError(str(exc)) from exc
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
        "quota_evidence": quota_record,
        "model": model,
        "campaign": campaign,
        "human_approval_required": True,
        "generation_executed": False,
    }


def execute_pkp0001_campaign(
    *,
    prepared: dict[str, Any],
    engine: ImageProductionEngine,
    quota_evidence: dict[str, Any] | None = None,
    generation_authorized: bool = False,
    editorial_approved: bool = False,
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
    if spend_limit_minor != 0:
        raise PapiKidsOrchestrationError("Le plafond de dépense doit rester strictement à zéro.")
    generator = getattr(engine, "generator", None)
    generator_models = getattr(generator, "models", None)
    if not isinstance(generator_models, tuple) or not generator_models or any(
        getattr(item, "free_confirmed", False) is not True for item in generator_models
    ):
        raise PapiKidsOrchestrationError(
            "Adaptateur non vérifié comme routeur de modèles explicitement gratuits ; exécution refusée."
        )
    selected = next((item for item in generator_models if item.model_id == prepared.get("model")), None)
    provider = getattr(generator, "provider", None)
    ledger = getattr(provider, "ledger", None)
    provider_costs = getattr(provider, "model_costs", None)
    account_ref = getattr(provider, "account_id", None)
    if selected is None or provider is None or ledger is None or not isinstance(provider_costs, dict):
        raise PapiKidsOrchestrationError("Fournisseur Cloudflare et ledger transactionnel requis.")
    try:
        current_quota = validate_quota_evidence(
            quota_evidence, provider="cloudflare", account_ref=account_ref,
            model_id=selected.model_id,
            estimated_units_per_image=selected.estimated_neurons_per_image,
            required_images=prepared.get("page_count"),
            provider_daily_limit=getattr(ledger, "daily_limit", None),
            provider_model_cost=provider_costs.get(selected.model_id),
        )
    except QuotaEvidenceError as exc:
        raise PapiKidsOrchestrationError(str(exc)) from exc
    if current_quota["evidence_ref"] != prepared.get("quota_evidence", {}).get("evidence_ref"):
        raise PapiKidsOrchestrationError("La preuve de quota a changé depuis la planification ; refaire le plan.")
    if editorial_approved is not True:
        raise PapiKidsOrchestrationError("Validation éditoriale humaine obligatoire avant génération.")
    authorize_generation = getattr(provider, "authorize_generation", None)
    if callable(authorize_generation):
        authorize_generation(True)
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
        "quota_evidence": current_quota,
        "editorial_approved": True,
        "human_approval_required": True,
    }


def prepare_pkp0001_campaign_from_registry(
    *,
    registry: Any,
    prompts_path: str | Path,
    character_bible_path: str | Path,
    account_refs: dict[str, str],
    quota_evidence_by_model: dict[str, dict[str, Any]],
    max_batch_size: int = 4,
    max_batch_units: int = 2_000,
) -> dict[str, Any]:
    """Select an eligible model from the governed registry, then plan offline."""
    from .image_provider_registry import ProviderRegistryError

    try:
        selected = registry.choose(
            account_refs=account_refs,
            quota_evidence_by_model=quota_evidence_by_model,
            required_images=EXPECTED_SCENES,
            spend_cap_minor=0,
        )
    except (ProviderRegistryError, AttributeError, TypeError) as exc:
        raise PapiKidsOrchestrationError(
            "Aucun fournisseur/modèle éligible dans le registre PAPI KIDS."
        ) from exc
    if selected.get("provider_id") != "cloudflare":
        raise PapiKidsOrchestrationError(
            "Le moteur d'exécution PKP-0001 ne prend actuellement en charge que Cloudflare."
        )
    model_id = selected["model_id"]
    evidence = quota_evidence_by_model.get(model_id)
    account_ref = account_refs.get("cloudflare")
    prepared = prepare_pkp0001_campaign(
        prompts_path=prompts_path,
        character_bible_path=character_bible_path,
        model=model_id,
        model_costs={model_id: selected["estimated_units_per_image"]},
        account_ref=account_ref,
        quota_evidence=evidence,
        max_batch_size=max_batch_size,
        max_batch_units=max_batch_units,
    )
    prepared["provider_selection"] = selected
    return prepared


def prepare_pkp0001_from_project_sources(
    *,
    project_root: str | Path,
    registry: Any,
    account_refs: dict[str, str],
    quota_evidence_by_model: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate the committed manuscript/bible/storyboard/prompts bundle and plan it."""
    root = Path(project_root).resolve()
    source_dir = root / "publishing" / "papi-kids" / BOOK_ID
    if not source_dir.is_dir() and os.environ.get("PAPI_KIDS_BUNDLED_SOURCES", "").lower() == "true":
        source_dir = Path(__file__).parent / "resources" / BOOK_ID
    manuscript_path = source_dir / "manuscript-v2.md"
    bible_path = source_dir / "character-bible-v1.md"
    storyboard_path = source_dir / "storyboard-v1.md"
    prompts_path = source_dir / "illustration-prompts-24-v1.md"
    manuscript = _read(manuscript_path)
    storyboard = _read(storyboard_path)
    prompts = _read(prompts_path)
    manuscript_pages = [
        int(value) for value in re.findall(r"^### Page (\d+)\s+[—-]", manuscript, re.MULTILINE)
    ]
    storyboard_pages = [
        int(value) for value in re.findall(r"^\|\s*(\d+)\s*\|", storyboard, re.MULTILINE)
    ]
    if manuscript_pages != list(range(1, EXPECTED_SCENES + 1)):
        raise PapiKidsOrchestrationError(
            "Le manuscrit V2 doit contenir exactement les pages narratives 1 à 24."
        )
    if storyboard_pages != list(range(1, EXPECTED_SCENES + 1)):
        raise PapiKidsOrchestrationError(
            "Le storyboard doit contenir exactement les pages 1 à 24 dans l'ordre."
        )
    _scene_sections(prompts)
    prepared = prepare_pkp0001_campaign_from_registry(
        registry=registry,
        prompts_path=prompts_path,
        character_bible_path=bible_path,
        account_refs=account_refs,
        quota_evidence_by_model=quota_evidence_by_model,
    )
    import hashlib
    prepared["source_bundle"] = {
        "manuscript_v2_sha256": hashlib.sha256(manuscript.encode("utf-8")).hexdigest(),
        "character_bible_sha256": hashlib.sha256(_read(bible_path).encode("utf-8")).hexdigest(),
        "storyboard_v1_sha256": hashlib.sha256(storyboard.encode("utf-8")).hexdigest(),
        "illustration_prompts_v1_sha256": hashlib.sha256(prompts.encode("utf-8")).hexdigest(),
        "manuscript_pages": len(manuscript_pages),
        "storyboard_pages": len(storyboard_pages),
        "source_status": "editorial_v2_not_human_approved",
    }
    prepared["human_editorial_approval_required"] = True
    return prepared
