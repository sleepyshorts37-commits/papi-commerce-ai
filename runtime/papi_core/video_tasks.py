"""File d'attente locale pour les vidéos YouTube soumises par le propriétaire.

Le module valide les liens et prépare dix tâches d'analyse. Il ne lit pas les vidéos,
n'ouvre pas de navigateur et ne génère aucune vue ou interaction artificielle.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
VIDEO_TASKS_FILE = ROOT / "data" / "video-tasks.json"
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
DEFAULT_AGENT_IDS = tuple(f"video-analyst-{index:02d}" for index in range(1, 11))


class VideoTaskError(ValueError):
    """Lien ou tâche vidéo invalide."""


def extract_youtube_video_id(url: str) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise VideoTaskError("Le lien YouTube est invalide.")
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in YOUTUBE_HOSTS:
        raise VideoTaskError("Seuls les liens HTTPS YouTube reconnus sont acceptés.")
    video_id = ""
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise VideoTaskError("Identifiant vidéo YouTube non reconnu.")
    return video_id


def create_video_task(
    *,
    task_id: str,
    url: str,
    submitted_by: str,
    created_at: str,
    agent_ids: tuple[str, ...] = DEFAULT_AGENT_IDS,
) -> dict[str, Any]:
    video_id = extract_youtube_video_id(url)
    if not isinstance(task_id, str) or not task_id.strip():
        raise VideoTaskError("task_id est obligatoire.")
    if not isinstance(submitted_by, str) or not submitted_by.strip():
        raise VideoTaskError("submitted_by est obligatoire.")
    if not isinstance(created_at, str) or not created_at.strip():
        raise VideoTaskError("created_at est obligatoire.")
    if len(agent_ids) != 10 or len(set(agent_ids)) != 10 or any(not x for x in agent_ids):
        raise VideoTaskError("L'équipe vidéo doit contenir exactement dix identifiants uniques.")
    return {
        "id": task_id,
        "video_url": url,
        "youtube_video_id": video_id,
        "submitted_by": submitted_by,
        "created_at": created_at,
        "status": "queued",
        "analysis_mode": "content_analysis_only",
        "agents": [
            {"agent_id": agent_id, "status": "pending", "observation": None}
            for agent_id in agent_ids
        ],
        "report_status": "pending",
        "artificial_views_allowed": False,
        "artificial_engagement_allowed": False,
        "autoplay_or_repeated_playback": False,
        "external_actions_enabled": False,
    }


def validate_video_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(task, dict):
        return ["La tâche vidéo doit être un objet."]
    try:
        extracted = extract_youtube_video_id(task.get("video_url"))
        if task.get("youtube_video_id") != extracted:
            errors.append("youtube_video_id ne correspond pas au lien.")
    except VideoTaskError as exc:
        errors.append(str(exc))
    if task.get("status") not in {"queued", "in_progress", "blocked", "completed", "cancelled"}:
        errors.append("Statut de tâche vidéo invalide.")
    agents = task.get("agents")
    if not isinstance(agents, list) or len(agents) != 10:
        errors.append("Une tâche doit affecter exactement dix agents.")
    else:
        ids = [item.get("agent_id") for item in agents if isinstance(item, dict)]
        if len(ids) != 10 or len(set(ids)) != 10:
            errors.append("Les dix agents doivent avoir des identifiants uniques.")
    if task.get("artificial_views_allowed") is not False:
        errors.append("Les vues artificielles doivent rester interdites.")
    if task.get("artificial_engagement_allowed") is not False:
        errors.append("L'engagement artificiel doit rester interdit.")
    if task.get("external_actions_enabled") is not False:
        errors.append("Les actions externes doivent rester désactivées.")
    return errors


def validate_video_task_registry(data: dict[str, Any]) -> list[str]:
    if not isinstance(data, dict) or data.get("project") != "PAPI COMMERCE AI":
        return ["Registre VIDEO TASKS invalide."]
    if set(data) - {"project", "schema_version", "tasks", "note"}:
        return ["Sections inconnues dans le registre VIDEO TASKS."]
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return ["tasks doit être une liste."]
    errors: list[str] = []
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        errors.extend(f"tasks[{index}]: {error}" for error in validate_video_task(task))
        if isinstance(task, dict):
            task_id = task.get("id")
            if isinstance(task_id, str):
                if task_id in seen:
                    errors.append(f"Identifiant de tâche vidéo dupliqué: {task_id}.")
                seen.add(task_id)
    return errors


def load_video_task_registry(path: Path = VIDEO_TASKS_FILE) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoTaskError("Impossible de lire le registre VIDEO TASKS.") from exc
    errors = validate_video_task_registry(data)
    if errors:
        raise VideoTaskError("; ".join(errors))
    return data


def build_video_report(task: dict[str, Any]) -> dict[str, Any]:
    errors = validate_video_task(task)
    if errors:
        raise VideoTaskError("; ".join(errors))
    observations = [
        {"agent_id": agent["agent_id"], "status": agent["status"], "observation": agent.get("observation")}
        for agent in task["agents"]
    ]
    completed = sum(agent["status"] == "completed" for agent in task["agents"])
    return {
        "task_id": task["id"],
        "youtube_video_id": task["youtube_video_id"],
        "agents_assigned": len(observations),
        "agents_completed": completed,
        "observations": observations,
        "report_status": "ready_for_consolidation" if completed == 10 else "incomplete",
        "view_count_generation": False,
    }
