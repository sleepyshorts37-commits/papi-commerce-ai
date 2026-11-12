"""Prototype LangGraph consultatif, sans modèle ni effet externe.

LangGraph reste une dépendance optionnelle : le noyau PAPI fonctionne sans lui.
Le graphe ne reçoit qu'une fonction de prévisualisation fournie explicitement.
"""
from __future__ import annotations

from typing import Any, Callable, TypedDict


class DemoState(TypedDict, total=False):
    request: str
    history: list[str]
    result: dict[str, Any]
    status: str
    error_code: str


class LangGraphUnavailable(RuntimeError):
    """LangGraph n'est pas installé dans cet environnement."""


def build_readonly_demo_graph(
    preview: Callable[[str], dict[str, Any]],
    *,
    checkpointer: Any | None = None,
) -> Any:
    """Construit un graphe de démonstration déterministe.

    `preview` doit être une fonction locale en lecture seule. Aucun outil,
    modèle, réseau, stockage PAPI ou worker n'est instancié ici.
    Un checkpointer n'est utilisé que s'il est explicitement injecté.
    """
    if not callable(preview):
        raise TypeError("preview doit être une fonction appelable.")

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise LangGraphUnavailable(
            "Installer le supplément optionnel LangGraph pour utiliser ce prototype."
        ) from exc

    def preview_node(state: DemoState) -> dict[str, Any]:
        request = state.get("request")
        if not isinstance(request, str) or not request.strip() or len(request) > 500:
            return {"status": "blocked", "error_code": "invalid_request"}

        history = state.get("history", [])
        if not isinstance(history, list):
            history = []
        safe_history = [item for item in history if isinstance(item, str)]
        safe_history = (safe_history + [request.strip()])[-10:]

        try:
            result = preview(request.strip())
            if not isinstance(result, dict):
                return {
                    "history": safe_history,
                    "status": "failed",
                    "error_code": "invalid_preview_result",
                }
        except Exception:
            # Ne pas exposer les messages d'exception, qui peuvent contenir
            # des données métier ou des secrets.
            return {
                "history": safe_history,
                "status": "failed",
                "error_code": "preview_error",
            }

        return {
            "history": safe_history,
            "result": result,
            "status": "completed",
            "error_code": "",
        }

    builder = StateGraph(DemoState)
    builder.add_node("readonly_preview", preview_node)
    builder.add_edge(START, "readonly_preview")
    builder.add_edge("readonly_preview", END)
    return builder.compile(checkpointer=checkpointer)
