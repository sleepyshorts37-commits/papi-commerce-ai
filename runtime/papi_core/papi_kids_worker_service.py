"""Supervised worker loop and server-only PostgreSQL connection factory."""
from __future__ import annotations

import os
import signal
import threading
import time
from typing import Any, Callable
from urllib.parse import urlsplit, parse_qs

from .papi_kids_editorial_worker import run_one_editorial_job


class PapiKidsWorkerConfigurationError(RuntimeError):
    """Worker is not safely configured."""


def create_postgres_connection_factory(
    *,
    env_var: str = "PAPI_KIDS_DATABASE_URL",
    allow_local: bool = False,
) -> Callable[[], Any]:
    """Create a server-only DB-API factory; never print or persist the DSN."""
    dsn = os.environ.get(env_var, "")
    if not dsn:
        raise PapiKidsWorkerConfigurationError("URL PostgreSQL serveur absente.")
    parsed = urlsplit(dsn)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise PapiKidsWorkerConfigurationError("URL PostgreSQL invalide.")
    if not parsed.username or not parsed.password:
        raise PapiKidsWorkerConfigurationError("Identifiants PostgreSQL serveur absents.")
    query = parse_qs(parsed.query)
    if query.get("sslmode", [""])[0] != "require":
        raise PapiKidsWorkerConfigurationError("sslmode=require obligatoire.")
    if not allow_local and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise PapiKidsWorkerConfigurationError("Base locale interdite en mode production.")

    def connect() -> Any:
        try:
            import psycopg
        except ImportError as exc:
            raise PapiKidsWorkerConfigurationError("Dépendance psycopg indisponible.") from exc
        return psycopg.connect(dsn)
    return connect


def run_worker_loop(
    connection_factory: Callable[[], Any],
    *,
    storage_root: str,
    worker_id: str,
    enabled: bool,
    max_jobs_per_cycle: int = 5,
    idle_sleep_seconds: float = 5.0,
    active_sleep_seconds: float = 0.25,
    max_cycles: int | None = None,
    stop_requested: Callable[[], bool] = lambda: False,
    sleep_fn: Callable[[float], Any] = time.sleep,
) -> dict[str, Any]:
    """Run bounded batches; no AI/image provider is ever invoked by this worker."""
    if enabled is not True:
        return {"status": "disabled", "processed": 0, "cycles": 0, "provider_calls": 0}
    if not isinstance(worker_id, str) or not 3 <= len(worker_id) <= 120:
        raise PapiKidsWorkerConfigurationError("Identifiant worker invalide.")
    if not isinstance(storage_root, str) or not storage_root:
        raise PapiKidsWorkerConfigurationError("Volume privé non configuré.")
    if not isinstance(max_jobs_per_cycle, int) or not 1 <= max_jobs_per_cycle <= 100:
        raise PapiKidsWorkerConfigurationError("Taille de lot invalide.")
    if not 0.1 <= idle_sleep_seconds <= 300 or not 0 <= active_sleep_seconds <= 30:
        raise PapiKidsWorkerConfigurationError("Intervalle de polling invalide.")

    processed = 0
    cycles = 0
    while not stop_requested() and (max_cycles is None or cycles < max_cycles):
        cycles += 1
        cycle_processed = 0
        for _ in range(max_jobs_per_cycle):
            if stop_requested():
                break
            result = run_one_editorial_job(
                connection_factory, storage_root=storage_root, worker_id=worker_id,
            )
            if result.get("status") == "idle":
                break
            if result.get("processed") is True:
                processed += 1
                cycle_processed += 1
        if stop_requested() or (max_cycles is not None and cycles >= max_cycles):
            break
        sleep_fn(active_sleep_seconds if cycle_processed else idle_sleep_seconds)
    return {
        "status": "stopped",
        "processed": processed,
        "cycles": cycles,
        "provider_calls": 0,
        "ai_calls": 0,
    }


def run_worker_from_environment() -> dict[str, Any]:
    """Production entry point. Requires explicit enablement and server-only env vars."""
    if os.environ.get("PAPI_KIDS_WORKER_ENABLED", "").lower() != "true":
        return {"status": "disabled", "processed": 0, "cycles": 0, "provider_calls": 0}
    worker_id = os.environ.get("PAPI_KIDS_WORKER_ID", "")
    storage_root = os.environ.get("PAPI_KIDS_PRIVATE_STORAGE_DIR", "")
    if not storage_root:
        raise PapiKidsWorkerConfigurationError("PAPI_KIDS_PRIVATE_STORAGE_DIR absent.")
    connection_factory = create_postgres_connection_factory()
    stop = threading.Event()
    previous_handlers = {}

    def request_stop(signum: int, frame: Any) -> None:
        stop.set()

    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, request_stop)
        except ValueError:
            # Non-main threads cannot register process signal handlers.
            pass
    try:
        return run_worker_loop(
            connection_factory,
            storage_root=storage_root,
            worker_id=worker_id,
            enabled=True,
            stop_requested=stop.is_set,
        )
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def main() -> int:
    run_worker_from_environment()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
