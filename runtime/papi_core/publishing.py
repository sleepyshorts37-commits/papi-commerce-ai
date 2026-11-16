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

    def save_update(self, project: dict[str, Any]) -> dict[str, Any]:
        """Remplace atomiquement un projet existant après validation."""
        validate_project(project)
        path = self.path_for(project["id"])
        if not path.exists():
            raise BookProjectError("Projet introuvable : création refusée lors d'une mise à jour.")
        payload = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            temporary.unlink(missing_ok=True)
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
        if task.get("status") not in {"backlog", "in_progress", "completed", "failed"}:
            raise BookProjectError("Statut de tâche invalide.")
        if not isinstance(task.get("attempts"), int) or not 0 <= task["attempts"] <= task.get("max_attempts", 0):
            raise BookProjectError("Compteur de tentatives invalide.")
        if not isinstance(task.get("output_refs"), list):
            raise BookProjectError("Références de livrables invalides.")
    if not isinstance(project.get("assets"), list) or not isinstance(project.get("reviews"), list):
        raise BookProjectError("Registre des livrables ou des revues invalide.")
    if project.get("release_package") is not None:
        package = project["release_package"]
        if not isinstance(package, dict) or package.get("approval_status") not in {"pending_owner", "approved", "rejected"}:
            raise BookProjectError("Dossier de livraison invalide.")
        if package.get("publication_status") != "not_published":
            raise BookProjectError("La publication doit rester une action externe explicitement autorisée.")
    if not isinstance(project.get("history"), list) or not project["history"]:
        raise BookProjectError("Historique d'audit absent.")
    if project.get("publication_approval_required") is not True:
        raise BookProjectError("L'approbation humaine avant publication est obligatoire.")

def transition_task(project_id: str, task_id: str, action: str, *, store: BookProjectStore,
                    actor: str = "owner", output_ref: str | None = None,
                    reason: str | None = None) -> dict[str, Any]:
    """Effectue une transition explicite ; aucune tâche n'est exécutée par cette fonction."""
    project = store.get(project_id)
    if project is None:
        raise BookProjectError("Projet introuvable.")
    task = next((item for item in project["tasks"] if item["id"] == task_id), None)
    if task is None:
        raise BookProjectError("Tâche introuvable dans ce projet.")
    now = _now()
    if action == "start":
        if task["status"] != "backlog":
            raise BookProjectError("Seule une tâche en backlog peut démarrer.")
        dependencies = {item["id"]: item["status"] for item in project["tasks"]}
        blocked = [dep for dep in task["dependencies"] if dependencies.get(dep) != "completed"]
        if blocked:
            raise BookProjectError("Dépendances non terminées : " + ", ".join(blocked))
        task["status"] = "in_progress"
        task["attempts"] += 1
        event = "task.started"
    elif action == "complete":
        if task["status"] != "in_progress":
            raise BookProjectError("Seule une tâche en cours peut être terminée.")
        if output_ref is not None:
            if not isinstance(output_ref, str) or not output_ref.strip() or len(output_ref) > 1000:
                raise BookProjectError("Référence de livrable invalide.")
            task["output_refs"].append(output_ref.strip())
        task["status"] = "completed"
        event = "task.completed"
    elif action == "fail":
        if task["status"] != "in_progress":
            raise BookProjectError("Seule une tâche en cours peut échouer.")
        if not isinstance(reason, str) or not reason.strip():
            raise BookProjectError("Un motif est obligatoire pour enregistrer un échec.")
        task["status"] = "failed"
        event = "task.failed"
    elif action == "retry":
        if task["status"] != "failed":
            raise BookProjectError("Seule une tâche en échec peut être relancée.")
        if task["attempts"] >= task["max_attempts"]:
            raise BookProjectError("Nombre maximal de tentatives atteint.")
        task["status"] = "backlog"
        event = "task.retry_requested"
    else:
        raise BookProjectError("Action inconnue. Actions autorisées : start, complete, fail, retry.")
    project["updated_at"] = now
    project["status"] = ("completed" if all(t["status"] == "completed" for t in project["tasks"])
                         else "in_progress" if any(t["status"] in {"in_progress", "completed"} for t in project["tasks"])
                         else "planned")
    details = {"task_id": task_id, "action": action}
    if output_ref is not None and action == "complete": details["output_ref"] = output_ref.strip()
    if reason is not None and action == "fail": details["reason"] = reason.strip()[:1000]
    project["history"].append({"at": now, "event": event, "actor": actor[:100], "details": details})
    return store.save_update(project)

def register_asset(project_id: str, asset: dict[str, Any], *, store: BookProjectStore,
                   actor: str = "owner") -> dict[str, Any]:
    """Enregistre les métadonnées d'un livrable ; aucun fichier n'est téléversé."""
    project = store.get(project_id)
    if project is None:
        raise BookProjectError("Projet introuvable.")
    required = {"id", "kind", "uri", "version", "sha256", "provenance", "status"}
    if not isinstance(asset, dict) or not required.issubset(asset):
        raise BookProjectError("Métadonnées du livrable incomplètes.")
    if not isinstance(asset["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", asset["id"]):
        raise BookProjectError("Identifiant de livrable invalide.")
    if any(item.get("id") == asset["id"] for item in project["assets"]):
        raise BookProjectError("Cet identifiant de livrable existe déjà.")
    if asset["status"] not in {"draft", "ready_for_review", "approved", "rejected"}:
        raise BookProjectError("Statut de livrable invalide.")
    if not isinstance(asset["version"], int) or asset["version"] < 1:
        raise BookProjectError("Version de livrable invalide.")
    if not isinstance(asset["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]):
        raise BookProjectError("Empreinte SHA-256 invalide.")
    for field in ("kind", "uri", "provenance"):
        if not isinstance(asset[field], str) or not asset[field].strip() or len(asset[field]) > 2000:
            raise BookProjectError(f"Champ {field} invalide.")
    if project["release_package"] is not None:
        raise BookProjectError("Dossier de livraison figé : créer une nouvelle version du projet.")
    item = dict(asset)
    item.setdefault("created_at", _now())
    project["assets"].append(item)
    project["updated_at"] = _now()
    project["history"].append({"at": project["updated_at"], "event": "asset.registered",
                               "actor": actor[:100], "details": {"asset_id": item["id"], "kind": item["kind"]}})
    return store.save_update(project)


def add_review(project_id: str, review: dict[str, Any], *, store: BookProjectStore,
               actor: str = "reviewer") -> dict[str, Any]:
    """Enregistre une revue avec séparation entre auteur et réviseur."""
    project = store.get(project_id)
    if project is None:
        raise BookProjectError("Projet introuvable.")
    required = {"id", "scope", "reviewer", "decision", "findings"}
    if not isinstance(review, dict) or not required.issubset(review):
        raise BookProjectError("Rapport de revue incomplet.")
    if not isinstance(review["id"], str) or not review["id"].strip():
        raise BookProjectError("Identifiant de revue invalide.")
    if any(item.get("id") == review["id"] for item in project["reviews"]):
        raise BookProjectError("Identifiant de revue déjà utilisé.")
    if review["decision"] not in {"approved", "changes_requested", "rejected"}:
        raise BookProjectError("Décision de revue invalide.")
    if not isinstance(review["reviewer"], str) or not review["reviewer"].strip():
        raise BookProjectError("Identité du réviseur obligatoire.")
    if not isinstance(actor, str) or review["reviewer"].strip().casefold() == actor.strip().casefold():
        raise BookProjectError("Le réviseur ne peut pas soumettre sa propre revue.")
    if not isinstance(review["findings"], list):
        raise BookProjectError("Les constats de revue doivent être une liste.")
    item = dict(review)
    item.setdefault("created_at", _now())
    project["reviews"].append(item)
    project["updated_at"] = _now()
    project["history"].append({"at": project["updated_at"], "event": "review.recorded",
                               "actor": actor[:100], "details": {"review_id": item["id"], "decision": item["decision"]}})
    return store.save_update(project)


def prepare_release_package(project_id: str, *, store: BookProjectStore,
                            metadata: dict[str, Any]) -> dict[str, Any]:
    """Fige le manifeste de livraison en attente d'approbation humaine."""
    project = store.get(project_id)
    if project is None:
        raise BookProjectError("Projet introuvable.")
    if project["release_package"] is not None:
        raise BookProjectError("Un dossier de livraison existe déjà.")
    if any(task["status"] != "completed" for task in project["tasks"]):
        raise BookProjectError("Toutes les tâches doivent être terminées.")
    if not project["assets"] or any(asset["status"] != "approved" for asset in project["assets"]):
        raise BookProjectError("Tous les livrables doivent être enregistrés et approuvés.")
    if not project["reviews"] or any(review["decision"] != "approved" for review in project["reviews"]):
        raise BookProjectError("Tous les rapports de revue doivent être approuvés.")
    if not isinstance(metadata, dict):
        raise BookProjectError("Métadonnées commerciales invalides.")
    package = {
        "id": project_id + "-release-v1",
        "created_at": _now(),
        "asset_ids": [asset["id"] for asset in project["assets"]],
        "metadata": metadata,
        "manifest_sha256": hashlib.sha256(json.dumps(project["assets"], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        "approval_status": "pending_owner",
        "publication_status": "not_published",
    }
    project["release_package"] = package
    project["updated_at"] = package["created_at"]
    project["history"].append({"at": package["created_at"], "event": "release.package_prepared",
                               "actor": "system", "details": {"package_id": package["id"], "approval_status": "pending_owner"}})
    return store.save_update(project)


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
        "assets": [], "reviews": [], "release_package": None,\n        "history": [{"at": now, "event": "project.created", "actor": "owner_request",
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
