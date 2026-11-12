"""Persistance Supabase/PostgREST avec contrôle optimiste et transitions atomiques."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .audit import validate_event


class StoreError(RuntimeError):
    """Erreur de configuration, de transport ou de cohérence du stockage."""


class SupabaseStore:
    """Stockage distant. Aucun secret n'est codé en dur ni journalisé."""

    def __init__(self, url: str | None = None, key: str | None = None, timeout: int = 15):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_KEY", "")
        self.timeout = timeout
        if not self.url.startswith("https://") or not self.key:
            raise StoreError("Configurer SUPABASE_URL (HTTPS) et SUPABASE_KEY dans l'environnement.")

    def _request(self, method: str, path: str, payload: Any = None, prefer: str | None = None):
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        request = Request(f"{self.url}/rest/v1/{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            raise StoreError(f"Supabase a répondu HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise StoreError(f"Échec de communication avec Supabase ({type(exc).__name__}).") from exc

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        rows = self._request("GET", f"papi_tasks?id=eq.{quote(task_id, safe='')}&select=task,version")
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue du stockage.")
        if not rows:
            return None
        return rows[0]

    def get_audit_events(self, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Lit une page bornée d'événements d'audit ; ne modifie jamais le journal."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise StoreError("limit doit être un entier compris entre 1 et 1000.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise StoreError("offset doit être un entier positif ou nul.")
        query = (
            "papi_audit_events"
            "?select=event_id,occurred_at,actor,action,entity_type,entity_id,details"
            f"&order=occurred_at.asc,event_id.asc&limit={limit}&offset={offset}"
        )
        rows = self._request("GET", query)
        if not isinstance(rows, list) or len(rows) > limit:
            raise StoreError("Réponse inattendue lors de la lecture du journal d'audit.")
        events = []
        try:
            for row in rows:
                validate_event(row)
                events.append(row)
        except (TypeError, ValueError) as exc:
            raise StoreError(f"Événement Supabase invalide : {exc}") from exc
        return events

    def get_agent_history(
        self,
        agent_id: str,
        tasks: list[dict[str, Any]],
        *,
        page_size: int = 500,
        max_pages: int = 20,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        """Construit un historique depuis Supabase en lecture seule.

        La lecture est paginée et bornée à 20 000 événements au maximum.
        Si la limite est atteinte, l'appel échoue plutôt que de présenter un
        historique partiel comme complet.
        """
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
            raise StoreError("max_pages doit être compris entre 1 et 20.")
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 1000:
            raise StoreError("page_size doit être compris entre 1 et 1000.")
        from .agent_history import AgentHistoryError, summarize_agent_history

        events: list[dict[str, Any]] = []
        for page in range(max_pages):
            batch = self.get_audit_events(limit=page_size, offset=page * page_size)
            events.extend(batch)
            if len(batch) < page_size:
                break
        else:
            # Une page pleine à la limite peut cacher d'autres lignes.
            raise StoreError("Historique trop volumineux : augmenter le traitement par lots dans une version dédiée.")
        try:
            return summarize_agent_history(agent_id, events, tasks, as_of=as_of)
        except AgentHistoryError as exc:
            raise StoreError(f"Impossible de calculer l'historique : {exc}") from exc

    def save_task(self, task: dict[str, Any], *, expected_version: int | None = None) -> int:
        """Insère une tâche (version 1) ou la met à jour si la version attendue correspond."""
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise StoreError("La tâche doit avoir un identifiant.")
        if expected_version is None:
            rows = self._request(
                "POST", "papi_tasks",
                {"id": task_id, "task": task, "version": 1},
                prefer="return=representation",
            )
            if not isinstance(rows, list) or not rows:
                raise StoreError("Insertion non confirmée.")
            return int(rows[0]["version"])
        if not isinstance(expected_version, int) or expected_version < 1:
            raise StoreError("Version attendue invalide.")
        rows = self._request(
            "PATCH",
            f"papi_tasks?id=eq.{quote(task_id, safe='')}&version=eq.{expected_version}",
            {"task": task, "version": expected_version + 1},
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Conflit de version : tâche modifiée ailleurs ou introuvable. Relire avant de réessayer.")
        return int(rows[0]["version"])

    def append_audit_event(self, event: dict[str, Any]) -> bool:
        validate_event(event)
        rows = self._request("POST", "papi_audit_events", event, prefer="return=representation")
        return isinstance(rows, list) and len(rows) == 1

    def commit_task_change(
        self, task: dict[str, Any], event: dict[str, Any], *, expected_version: int
    ) -> int:
        """Enregistre tâche + audit dans une seule transaction PostgreSQL via RPC."""
        validate_event(event)
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or event["entity_type"] != "task" or event["entity_id"] != task_id:
            raise StoreError("La tâche et l'événement d'audit doivent désigner la même mission.")
        if not isinstance(expected_version, int) or expected_version < 1:
            raise StoreError("Version attendue invalide.")
        result = self._request(
            "POST",
            "rpc/papi_commit_task_change",
            {
                "p_task_id": task_id,
                "p_expected_version": expected_version,
                "p_task": task,
                "p_event": event,
            },
        )
        if not isinstance(result, int) or result != expected_version + 1:
            raise StoreError("La transaction n'a pas retourné une nouvelle version valide.")
        return result

    def assign_task_and_save(
        self, task_id: str, *, assigner_id: str, assignee_id: str,
        agents: dict[str, dict[str, Any]], identity_registry: dict[str, Any],
        expected_version: int,
    ) -> tuple[dict[str, Any], int]:
        """Affecte une tâche et son audit dans une transaction PostgreSQL atomique.

        L'appelant doit authentifier cryptographiquement l'acteur avant cet appel.
        Aucun worker n'est lancé et aucune action externe n'est exécutée.
        """
        from .task_assignment import TaskAssignmentError, assign_task

        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
            raise StoreError("Version attendue invalide.")
        current = self.get_task(task_id)
        if not current or current.get("version") != expected_version:
            raise StoreError("Conflit de version ou tâche introuvable ; relire avant de réessayer.")
        if not isinstance(current.get("task"), dict) or current["task"].get("id") != task_id:
            raise StoreError("Enregistrement de tâche incohérent.")
        try:
            updated, event = assign_task(
                current["task"],
                assigner_id=assigner_id,
                assignee_id=assignee_id,
                agents=agents,
                identity_registry=identity_registry,
            )
        except TaskAssignmentError as exc:
            raise StoreError(f"Affectation refusée : {exc}") from exc
        version = self.commit_task_change(updated, event, expected_version=expected_version)
        return updated, version

    def transition_and_save(
        self, task_id: str, new_status: str, *, actor: str,
        expected_version: int, reason: str = "", evidence: list[str] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Relit, vérifie la version, calcule la transition puis la valide atomiquement."""
        from .state_machine import TransitionError, transition_task

        current = self.get_task(task_id)
        if not current or current.get("version") != expected_version:
            raise StoreError("Conflit de version ou mission introuvable ; relire avant de réessayer.")
        try:
            updated, event = transition_task(
                current["task"], new_status, actor=actor, reason=reason, evidence=evidence
            )
        except (KeyError, TransitionError) as exc:
            raise StoreError(f"Transition refusée : {exc}") from exc
        version = self.commit_task_change(updated, event, expected_version=expected_version)
        return updated, version

    def approve_and_save(
        self, task_id: str, *, approver: str, decision: str,
        expected_version: int, reason: str = "",
    ) -> tuple[dict[str, Any], int]:
        """Enregistre une approbation explicite sans déclencher la mission."""
        from .state_machine import TransitionError, approve_task

        current = self.get_task(task_id)
        if not current or current.get("version") != expected_version:
            raise StoreError("Conflit de version ou mission introuvable ; relire avant de réessayer.")
        try:
            updated, event = approve_task(
                current["task"], approver=approver, decision=decision, reason=reason
            )
        except (KeyError, TransitionError) as exc:
            raise StoreError(f"Approbation refusée : {exc}") from exc
        version = self.commit_task_change(updated, event, expected_version=expected_version)
        return updated, version
