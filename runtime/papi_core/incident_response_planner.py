"""Plans de réponse aux incidents PAPI : recommandations uniquement, sans exécution."""
from __future__ import annotations

from typing import Any


class IncidentResponsePlannerError(ValueError):
    """Instantané d'incidents invalide."""


_CATEGORY_GUIDANCE = {
    "worker": (
        "Confirmer le statut du worker depuis une source fiable.",
        "Examiner les heartbeats et journaux techniques autorisés.",
        "Faire valider le diagnostic par le responsable technique.",
    ),
    "security": (
        "Suspendre toute décision d'accès automatisée et préserver les éléments de preuve.",
        "Faire vérifier l'identité et les permissions par un responsable habilité.",
        "Demander une validation du propriétaire avant toute modification d'accès.",
    ),
    "job": (
        "Vérifier l'état courant de la tâche et son historique d'audit.",
        "Identifier la cause de l'échec ou de l'expiration du bail.",
        "Soumettre toute reprise ou réaffectation à une approbation explicite.",
    ),
    "platform": (
        "Vérifier la disponibilité du service concerné à partir d'une source autorisée.",
        "Consulter les journaux et l'état des dépendances.",
        "Faire approuver toute opération corrective avant exécution.",
    ),
    "data": (
        "Préserver les données et vérifier l'intégrité des sources.",
        "Identifier précisément le périmètre affecté sans exposer de données sensibles.",
        "Faire valider toute correction ou restauration avant exécution.",
    ),
    "integration": (
        "Vérifier la connexion et les réponses du fournisseur sans révéler de secrets.",
        "Contrôler les quotas et limites documentés.",
        "Faire approuver tout changement de configuration ou achat de crédits.",
    ),
    "other": (
        "Recueillir des éléments factuels auprès du responsable concerné.",
        "Évaluer l'impact et le périmètre de l'incident.",
        "Soumettre une proposition corrective au propriétaire.",
    ),
}


def build_incident_response_plan(incident_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Construit un plan trié par priorité ; aucune action n'est lancée."""
    if not isinstance(incident_snapshot, dict):
        raise IncidentResponsePlannerError("incident_snapshot doit être un objet.")
    incidents = incident_snapshot.get("incidents")
    if not isinstance(incidents, list):
        raise IncidentResponsePlannerError("incidents doit être une liste.")

    plans = []
    seen = set()
    for incident in incidents:
        if not isinstance(incident, dict):
            raise IncidentResponsePlannerError("Incident invalide.")
        incident_id = incident.get("incident_id")
        severity = incident.get("severity")
        category = incident.get("category")
        status = incident.get("status")
        if not isinstance(incident_id, str) or not incident_id.strip() or len(incident_id) > 120:
            raise IncidentResponsePlannerError("incident_id invalide.")
        if incident_id in seen:
            raise IncidentResponsePlannerError("incident_id dupliqué.")
        seen.add(incident_id)
        if severity not in {"info", "warning", "critical"}:
            raise IncidentResponsePlannerError("Gravité inconnue.")
        if category not in _CATEGORY_GUIDANCE:
            raise IncidentResponsePlannerError("Catégorie inconnue.")
        if status not in {"open", "acknowledged", "resolved"}:
            raise IncidentResponsePlannerError("Statut inconnu.")
        if status == "resolved":
            continue

        if severity == "critical":
            priority, response_window, approval = 1, "immediate_review", "owner_or_authorized_manager"
        elif severity == "warning":
            priority, response_window, approval = 2, "next_review_cycle", "responsible_manager"
        else:
            priority, response_window, approval = 3, "routine_review", "responsible_manager"

        plans.append({
            "incident_id": incident_id,
            "priority": priority,
            "severity": severity,
            "category": category,
            "incident_status": status,
            "response_window": response_window,
            "approval_required_from": approval,
            "steps": [
                {"sequence": index, "action": action, "execution": "manual_review_only"}
                for index, action in enumerate(_CATEGORY_GUIDANCE[category], start=1)
            ],
            "prohibited_without_explicit_owner_approval": [
                "restart_worker", "retry_job", "reassign_job", "change_permissions",
                "modify_data", "send_external_notification", "spend_money",
            ],
            "owner_escalation_required": severity == "critical" or category == "security",
            "execution_authorized": False,
        })

    plans.sort(key=lambda item: (item["priority"], item["incident_id"]))
    return {
        "status": "plan_preview_only",
        "plans": plans,
        "summary": {
            "incidents_received": len(incidents),
            "plans_created": len(plans),
            "resolved_incidents_excluded": sum(
                1 for item in incidents if isinstance(item, dict) and item.get("status") == "resolved"
            ),
            "critical_plans": sum(1 for item in plans if item["severity"] == "critical"),
        },
        "read_only": True,
        "writes_performed": 0,
        "actions_executed": 0,
        "notifications_sent": 0,
        "financial_actions_performed": 0,
    }
