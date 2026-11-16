"""Socle ONE PROMPT de PAPI KIDS PUBLISHING : création d'un plan local, sans exécution."""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULTS = {"language": "fr", "age_range": "6-9", "book_type": "illustrated_story", "market": "Amazon KDP", "tone": "warm and adventurous"}
TASK_BLUEPRINT = [
    ("market_research", "MARKET RESEARCH", "Étudier le marché et définir un angle original", []),
    ("story_outline", "STORY ARCHITECT", "Créer le synopsis et le plan narratif", ["market_research"]),
    ("manuscript", "CHILDREN WRITER", "Rédiger le manuscrit complet", ["story_outline"]),
    ("editorial_review", "EDUCATIONAL EXPERT", "Relire et valider l'adaptation à l'âge", ["manuscript"]),
    ("character_bible", "CHARACTER DESIGNER", "Créer la bible des personnages", ["editorial_review"]),
    ("art_direction", "ART DIRECTOR", "Définir la direction artistique originale", ["character_bible"]),
    ("illustrations", "ILLUSTRATION TEAM", "Produire et contrôler les illustrations", ["art_direction"]),
    ("interior_layout", "BOOK DESIGNER", "Composer l'intérieur du livre", ["illustrations", "editorial_review"]),
    ("cover", "COVER DESIGNER", "Créer la couverture aux dimensions calculées", ["interior_layout"]),
    ("kdp_preflight", "KDP SPECIALIST", "Contrôler les fichiers et préparer les métadonnées", ["cover", "interior_layout"]),
    ("independent_quality", "QUALITY CONTROL / MARIAMA", "Effectuer le contrôle qualité indépendant", ["kdp_preflight"]),
    ("rights_review", "IP & COPYRIGHT", "Contrôler les droits et risques de propriété intellectuelle", ["independent_quality"]),
    ("human_approval", "OWNER", "Obtenir l'approbation humaine avant publication", ["rights_review"]),
]

class BookProjectError(ValueError):
    """Erreur de requête ou de dossier de livre."""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def _clean_prompt(prompt: str) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise BookProjectError("La demande de livre ne peut pas être vide.")
    value = prompt.strip()
    if len(value) > 12000:
        raise BookProjectError("La demande dépasse la limite de 12 000 caractères.")
    return value

def interpret_brief(prompt: str) -> dict[str, Any]:
    """Extraction prudente ; toute valeur non fournie reste une hypothèse visible."""
    value = _clean_prompt(prompt)
    age = re.search(r"(?:enfants? de |âge de |âgés? de )(\d{1,2})\s*(?:à|[-–])\s*(\d{1,2})\s*ans", value, re.I)
    english = bool(re.search(r"\b(in english|en anglais)\b", value, re.I))
    activity = bool(re.search(r"\b(activités|coloriage|puzzles?)\b", value, re.I))
    brief = {
        "original_request": value,
        "language": "en" if english else "fr",
        "age_range": f"{age.group(1)}-{age.group(2)}" if age else DEFAULTS["age_range"],
        "book_type": "activity_book" if activity else DEFAULTS["book_type"],
        "market": DEFAULTS["market"],
        "tone": DEFAULTS["tone"],
        "theme": None,
        "title": None,
        "assumptions": [],
        "requires_owner_review": True,
    }
    if not english: brief["assumptions"].append("language")
    if not age: brief["assumptions"].append("age_range")
    if not activity: brief["assumptions"].append("book_type")
    brief["assumptions"].extend(["market", "tone"])
    return brief

def build_tasks(project_id: str) -> list[dict[str, Any]]:
    return [{
        "id": f"{project_id}-{key}", "key": key, "title": title, "role": role,
        "dependencies": [f"{project_id}-{dep}" for dep in deps],
        "status": "backlog", "attempts": 0, "max_attempts": 3,
        "output_refs": [], "execution_enabled": False,
    } for key, role, title, deps in TASK_BLUEPRINT]

class BookProjectStore:
    """Stockage JSON local, création exclusive et permissions restrictives."""
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, project_id: str) -> Path:
        if not re.fullmatch(r"PKP-[0-9a-f]{16}", project_id):
            raise BookProjectError("Identifiant de projet invalide.")
        return self.directory / f"{project_id}.json"

    def get(self, project_id: str) -> dict[str, Any] | None:
        path = self.path_for(project_id)
        if not path.exists(): return None
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BookProjectError("Dossier de livre illisible ou corrompu.") from exc
        validate_project(data)
        return data

    def save_new(self, project: dict[str, Any]) -> dict[str, Any]:
        validate_project(project)
        path = self.path_for(project["id"])
        payload = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try: descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            existing = self.get(project["id"])
            if existing and existing["request_hash"] == project["request_hash"]: return existing
            raise BookProjectError("Conflit d'identifiant : relire le projet avant toute reprise.")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return project

def validate_project(project: dict[str, Any]) -> None:
    if not isinstance(project, dict) or project.get("schema_version") != SCHEMA_VERSION:
        raise BookProjectError("Version ou structure de projet invalide.")
    if not re.fullmatch(r"PKP-[0-9a-f]{16}", str(project.get("id", ""))):
        raise BookProjectError("Identifiant de projet invalide.")
    tasks = project.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(TASK_BLUEPRINT):
        raise BookProjectError("Le plan de production est incomplet.")
    ids = {task.get("id") for task in tasks if isinstance(task, dict)}
    if len(ids) != len(tasks): raise BookProjectError("Identifiants de tâches absents ou dupliqués.")
    for task in tasks:
        if not isinstance(task, dict) or not set(task.get("dependencies", [])).issubset(ids):
            raise BookProjectError("Dépendance de tâche inconnue.")
        if task.get("execution_enabled") is not False:
            raise BookProjectError("L'exécution automatique doit rester désactivée.")
    if project.get("publication_approval_required") is not True:
        raise BookProjectError("L'approbation humaine avant publication est obligatoire.")

def create_book_project(prompt: str, *, store: BookProjectStore) -> dict[str, Any]:
    """Crée un projet idempotent à partir d'une seule demande utilisateur."""
    value = _clean_prompt(prompt)
    request_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    project_id = "PKP-" + request_hash[:16]
    existing = store.get(project_id)
    if existing: return existing
    now = _now()
    project = {
        "schema_version": SCHEMA_VERSION, "id": project_id, "status": "planned",
        "created_at": now, "updated_at": now, "request_hash": request_hash,
        "brief": interpret_brief(value), "tasks": build_tasks(project_id),
        "history": [{"at": now, "event": "project.created", "actor": "owner_request",
                     "details": {"task_count": len(TASK_BLUEPRINT), "execution_enabled": False}}],
        "execution_enabled": False, "publication_approval_required": True,
        "production_note": "Plan créé uniquement : aucun texte, visuel ou fichier de livre n'a encore été généré.",
    }
    return store.save_new(project)

def get_project_summary(project: dict[str, Any]) -> dict[str, Any]:
    validate_project(project)
    return {"id": project["id"], "status": project["status"], "task_count": len(project["tasks"]),
            "planned_tasks": sum(task["status"] == "backlog" for task in project["tasks"]),
            "execution_enabled": project["execution_enabled"],
            "publication_approval_required": project["publication_approval_required"]}
