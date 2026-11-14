"""Contrat de préparation et garde-fous pour une future synchronisation."""

from __future__ import annotations

from typing import Any


class SyncReadinessError(ValueError):
    """Aperçu de réconciliation incomplet ou non conforme."""


def build_sync_readiness_report(preview: dict[str, Any]) -> dict[str, Any]:
    """Valide le contrat de prévisualisation sans déclencher d'action distante."""
    if not isinstance(preview, dict):
        raise SyncReadinessError("Un aperçu de réconciliation est requis.")
    if preview.get("mode") != "preview_only" or preview.get("writes_performed") is not False:
        raise SyncReadinessError("Seul un aperçu explicitement sans écriture est accepté.")
    if not isinstance(preview.get("actor"), str) or not preview["actor"].strip():
        raise SyncReadinessError("Identité d'agent absente.")
    counts = preview.get("counts")
    buckets = ("local_only", "remote_only", "identical", "conflicts")
    if not isinstance(counts, dict) or any(
        type(counts.get(key)) is not int or counts[key] < 0 for key in buckets
    ):
        raise SyncReadinessError("Compteurs de réconciliation invalides.")
    for section in ("memory", "messages"):
        data = preview.get(section)
        if not isinstance(data, dict):
            raise SyncReadinessError("Résultat mémoire/messages incomplet.")
        for bucket in buckets:
            rows = data.get(bucket)
            if not isinstance(rows, list):
                raise SyncReadinessError("Catégorie de résultat invalide.")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("record_id"), str):
                    raise SyncReadinessError("Référence de résultat invalide.")
                if row.get("type") not in {"memory", "message"}:
                    raise SyncReadinessError("Type de résultat invalide.")
    actual = {
        key: len(preview["memory"][key]) + len(preview["messages"][key])
        for key in buckets
    }
    if actual != counts:
        raise SyncReadinessError("Les compteurs ne correspondent pas aux résultats.")
    blockers = [
        "Aucun projet Supabase de test n'a été validé dans cette mission.",
        "Aucune procédure de transfert avec approbation humaine n'est activée.",
        "Aucun test inter-instances réel n'a été exécuté.",
        "La revue indépendante de sécurité reste obligatoire avant production.",
    ]
    if counts["conflicts"] or counts["local_only"] or counts["remote_only"]:
        blockers.append("Des différences nécessitent une revue humaine avant toute décision.")
    return {
        "status": "preview_ready",
        "sync_enabled": False,
        "writes_performed": False,
        "actor": preview["actor"],
        "counts": counts.copy(),
        "requires_human_review": bool(
            counts["conflicts"] or counts["local_only"] or counts["remote_only"]
        ),
        "blockers": blockers,
        "next_gate": "validation_humaine_et_tests_inter_instances",
    }
