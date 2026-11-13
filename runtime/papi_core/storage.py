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
    """Erreur de stockage avec code de reprise sûr, sans analyser le message."""
    def __init__(self, message: str, *, retry_code: str | None = None):
        super().__init__(message)
        allowed = {None, "temporarily_unavailable", "rate_limited",
                   "connection_reset", "service_timeout"}
        if retry_code not in allowed:
            raise ValueError("retry_code non autorisé")
        self.retry_code = retry_code


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
            retry_code = (
                "rate_limited" if exc.code == 429 else
                "service_timeout" if exc.code in {408, 504} else
                "temporarily_unavailable" if exc.code in {425, 500, 502, 503} else None
            )
            raise StoreError(f"Supabase a répondu HTTP {exc.code}.",
                             retry_code=retry_code) from exc
        except (URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            retry_code = (
                "service_timeout" if isinstance(reason, TimeoutError) else
                "connection_reset" if isinstance(reason, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)) else
                "temporarily_unavailable"
            )
            raise StoreError(f"Échec de communication avec Supabase ({type(exc).__name__}).",
                             retry_code=retry_code) from exc
        except json.JSONDecodeError as exc:
            raise StoreError("Réponse JSON invalide du stockage.") from exc

    def request(self, method: str, path: str, payload: Any = None, prefer: str | None = None):
        """Interface publique stable pour les adaptateurs internes PostgREST.

        Les appels doivent rester internes au backend de confiance. Ne jamais
        transmettre la clé serveur ni exposer cette méthode à un agent.
        """
        return self._request(method, path, payload, prefer)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        rows = self._request("GET", f"papi_tasks?id=eq.{quote(task_id, safe='')}&select=task,version")
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue du stockage.")
        if not rows:
            return None
        return rows[0]

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
