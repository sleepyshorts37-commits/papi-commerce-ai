"""Planificateur déterministe : calcule les échéances sans exécuter de tâche."""
from __future__ import annotations

import json
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES_FILE = ROOT / "data" / "schedules.json"
SCHEDULE_TYPES = {"daily", "weekly"}
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")


class SchedulerError(ValueError):
    """Définition de planification invalide."""


def validate_schedule(schedule: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(schedule, dict):
        return ["Une planification doit être un objet."]
    required = {"id", "title", "type", "time", "timezone", "enabled", "task_template", "owner_approval_required"}
    missing = required - schedule.keys()
    extra = schedule.keys() - required - {"weekdays", "last_run_at"}
    if missing:
        errors.append("Champs manquants: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("Champs inconnus: " + ", ".join(sorted(extra)))
    if missing:
        return errors
    if not isinstance(schedule["id"], str) or not ID_RE.fullmatch(schedule["id"]):
        errors.append("id invalide.")
    if not isinstance(schedule["title"], str) or not schedule["title"].strip() or len(schedule["title"]) > 120:
        errors.append("title invalide.")
    if schedule["type"] not in SCHEDULE_TYPES:
        errors.append("type doit être daily ou weekly.")
    if not isinstance(schedule["time"], str) or not TIME_RE.fullmatch(schedule["time"]):
        errors.append("time doit être au format HH:MM.")
    if not isinstance(schedule["timezone"], str):
        errors.append("timezone invalide.")
    else:
        try:
            ZoneInfo(schedule["timezone"])
        except ZoneInfoNotFoundError:
            errors.append("Fuseau horaire inconnu.")
    if not isinstance(schedule["enabled"], bool) or not isinstance(schedule["owner_approval_required"], bool):
        errors.append("enabled et owner_approval_required doivent être booléens.")
    if schedule["type"] == "weekly":
        weekdays = schedule.get("weekdays")
        if not isinstance(weekdays, list) or not weekdays or any(
            isinstance(day, bool) or not isinstance(day, int) or day not in range(7) for day in weekdays
        ) or len(set(weekdays)) != len(weekdays):
            errors.append("weekdays doit contenir des jours ISO uniques (0=lundi à 6=dimanche).")
    elif "weekdays" in schedule:
        errors.append("weekdays ne s'applique qu'aux planifications weekly.")
    template = schedule["task_template"]
    if not isinstance(template, dict) or not isinstance(template.get("handler"), str) or not template["handler"].strip():
        errors.append("task_template.handler obligatoire.")
    if not isinstance(template, dict) or not isinstance(template.get("payload", {}), dict):
        errors.append("task_template.payload doit être un objet.")
    last_run = schedule.get("last_run_at")
    if last_run is not None:
        if not isinstance(last_run, str):
            errors.append("last_run_at doit être une date ISO 8601.")
        else:
            try:
                parsed = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    errors.append("last_run_at doit inclure un fuseau horaire.")
            except ValueError:
                errors.append("last_run_at invalide.")
    return errors


def load_schedules(path: Path = SCHEDULES_FILE) -> list[dict[str, Any]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchedulerError("Impossible de lire le registre des planifications.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("schedules"), list):
        raise SchedulerError("Le fichier doit contenir une liste schedules.")
    seen: set[str] = set()
    for schedule in data["schedules"]:
        errors = validate_schedule(schedule)
        if errors:
            raise SchedulerError("; ".join(errors))
        if schedule["id"] in seen:
            raise SchedulerError(f"Identifiant de planification dupliqué: {schedule['id']}")
        seen.add(schedule["id"])
    return data["schedules"]


def due_schedules(
    *, now: datetime | None = None, path: Path = SCHEDULES_FILE,
) -> list[dict[str, Any]]:
    """Retourne les échéances à examiner ; n'enfile ni ne lance aucun travail."""
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        raise SchedulerError("now doit inclure un fuseau horaire.")
    due = []
    for schedule in load_schedules(path):
        if not schedule["enabled"]:
            continue
        local_now = current.astimezone(ZoneInfo(schedule["timezone"]))
        hour, minute = map(int, schedule["time"].split(":"))
        scheduled_today = datetime.combine(local_now.date(), time(hour, minute), tzinfo=local_now.tzinfo)
        if schedule["type"] == "weekly" and local_now.weekday() not in schedule["weekdays"]:
            continue
        if local_now < scheduled_today:
            continue
        last_run = schedule.get("last_run_at")
        if last_run:
            last = datetime.fromisoformat(last_run.replace("Z", "+00:00")).astimezone(local_now.tzinfo)
            if last.date() >= local_now.date():
                continue
        due.append({
            "schedule_id": schedule["id"],
            "title": schedule["title"],
            "due_at": scheduled_today.isoformat(),
            "timezone": schedule["timezone"],
            "task_template": schedule["task_template"],
            "owner_approval_required": schedule["owner_approval_required"],
            "status": "awaiting_scheduler_review",
        })
    return due
