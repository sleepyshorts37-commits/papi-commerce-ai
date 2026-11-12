"""Pont de prévisualisation supervision -> incidents, strictement sans écriture."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any


class IncidentBridgeError(ValueError):
    """Rapport de supervision invalide."""


# Le texte libre du diagnostic n'est jamais recopié dans le journal.
_MAPPINGS = {
    "worker_offline": ("critical", "worker", "Worker signalé hors ligne", "Vérifier sa disponibilité et ses journaux avant toute intervention."),
    "worker_suspended": ("warning", "worker", "Worker suspendu", "Faire vérifier son statut par le responsable."),
    "worker_status_unknown": ("warning", "worker", "Statut du worker inconnu", "Confirmer le statut depuis une source fiable."),
    "identity_invalid_or_permissions_mismatch": ("critical", "security", "Identité ou permissions du worker non conformes", "Vérifier la fiche d’identité et la parité des permissions."),
    "heartbeat_unverified": ("warning", "worker", "Heartbeat du worker non vérifié", "Vérifier la télémétrie ; l’absence de heartbeat ne prouve pas une panne."),
    "heartbeat_stale": ("critical", "worker", "Heartbeat du worker obsolète", "Vérifier la connexion et les journaux ; aucune relance automatique."),
    "lease_expired": ("critical", "job", "Bail de tâche expiré", "Examiner le worker propriétaire et le bail ; reprise manuelle après validation."),
    "retry_exhausted": ("critical", "job", "Nombre maximal de tentatives atteint", "Analyser la cause puis demander une approbation avant toute reprise."),
    "repeated_failures": ("warning", "job", "Échecs répétés d’une tâche", "Examiner les erreurs récentes avant toute nouvelle tentative."),
}
_EXPECTED_SCOPE = {
    "worker_offline": "worker", "worker_suspended": "worker",
    "worker_status_unknown": "worker", "identity_invalid_or_permissions_mismatch": "worker",
    "heartbeat_unverified": "worker", "heartbeat_stale": "worker",
    "lease_expired": "job", "retry_exhausted": "job", "repeated_failures": "job",
}


def _valid_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise IncidentBridgeError("as_of doit être une date ISO-8601 avec fuseau.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IncidentBridgeError("as_of invalide.") from exc
    if parsed.tzinfo is None:
        raise IncidentBridgeError("as_of doit inclure un fuseau horaire.")
    return value


def build_incident_report_candidates(supervision_report: dict[str, Any]) -> dict[str, Any]:
    """Convertit les anomalies connues en événements candidats ; ne persiste rien."""
    if not isinstance(supervision_report, dict):
        raise IncidentBridgeError("Le rapport de supervision doit être un objet.")
    if supervision_report.get("read_only") is not True:
        raise IncidentBridgeError("Le rapport source doit être explicitement en lecture seule.")
    as_of = _valid_timestamp(supervision_report.get("as_of"))
    issues = supervision_report.get("issues")
    if not isinstance(issues, list):
        raise IncidentBridgeError("issues doit être une liste.")

    candidates = []
    skipped_unknown = 0
    seen = set()
    for issue in issues:
        if not isinstance(issue, dict):
            raise IncidentBridgeError("Anomalie de supervision invalide.")
        code = issue.get("code")
        if code not in _MAPPINGS:
            skipped_unknown += 1
            continue
        severity, category, summary, recommendation = _MAPPINGS[code]
        scope = issue.get("scope")
        subject_id = issue.get("subject_id")
        if scope != _EXPECTED_SCOPE[code]:
            raise IncidentBridgeError("Portée incohérente pour le code d’anomalie.")
        if not isinstance(subject_id, str) or not subject_id.strip() or len(subject_id) > 120:
            raise IncidentBridgeError("subject_id invalide.")
        if issue.get("severity") != severity:
            raise IncidentBridgeError("Gravité incohérente pour le code d’anomalie.")
        if issue.get("action_executed") is not False:
            raise IncidentBridgeError("Une anomalie ayant déclenché une action ne peut être convertie.")
        fingerprint = "|".join((as_of, code, scope, subject_id))
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        incident_id = "incident-" + digest[:48]
        if incident_id in seen:
            raise IncidentBridgeError("Anomalie dupliquée dans le rapport source.")
        seen.add(incident_id)
        candidates.append({
            "event": {
                "event_id": "event-" + digest[:48],
                "occurred_at": as_of,
                "actor": "cheikh-fall",
                "action": "incident.reported",
                "entity_type": "incident",
                "entity_id": incident_id,
                "details": {
                    "severity": severity, "category": category,
                    "summary": f"{summary} : {subject_id}",
                    "recommendation": recommendation,
                },
            },
            "source": {"code": code, "scope": scope, "subject_id": subject_id},
        })

    candidates.sort(key=lambda item: item["event"]["entity_id"])
    return {
        "status": "preview_only",
        "report_candidates": candidates,
        "summary": {"candidates": len(candidates), "unknown_issues_skipped": skipped_unknown},
        "read_only": True,
        "writes_performed": 0,
        "events_appended": 0,
        "notifications_sent": 0,
        "external_actions_performed": 0,
    }
