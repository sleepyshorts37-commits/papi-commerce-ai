#!/usr/bin/env python3
"""Local-only PostgreSQL integration/concurrency tests for migration 013.

Requires psql and PAPI_TEST_DATABASE_URL pointing to localhost/loopback.
Each reservation is executed by a separate psql process and DB session.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "infra/supabase/migrations/013_shared_provider_quota_ledger.sql"
CONTRACT_TEST = ROOT / "infra/supabase/tests/013_shared_provider_quota_ledger.sql"
AUDIT_QUERY = ROOT / "scripts/audit_shared_quota_ledger.sql"
DAY = "2099-01-01"
DAILY_LIMIT = 100
ESTIMATE = 10


def run_psql(database_url: str, sql: str, *, file: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-d", database_url]
    if file is not None:
        command += ["-f", str(file)]
    else:
        command += ["-At", "-c", sql]
    return subprocess.run(command, text=True, capture_output=True, check=False)


def assert_local_database(database_url: str) -> None:
    parsed = urlparse(database_url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise SystemExit("Refus: PAPI_TEST_DATABASE_URL doit être une URL PostgreSQL.")
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise SystemExit(
            "Refus de sécurité : la base de test doit être locale "
            "(localhost, 127.0.0.1 ou ::1). Aucun hôte distant n'est accepté."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-migration", action="store_true",
                        help="ne pas appliquer la migration 013 (base locale déjà préparée)")
    args = parser.parse_args()

    database_url = os.environ.get("PAPI_TEST_DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("Définir PAPI_TEST_DATABASE_URL avec une URL PostgreSQL locale.")
    assert_local_database(database_url)
    if shutil.which("psql") is None:
        raise SystemExit("psql est introuvable ; installer le client PostgreSQL.")

    if not args.skip_migration:
        result = run_psql(database_url, "", file=MIGRATION)
        if result.returncode:
            sys.stderr.write(result.stderr)
            return result.returncode

    contract = run_psql(database_url, "", file=CONTRACT_TEST)
    if contract.returncode:
        sys.stderr.write(contract.stdout + contract.stderr)
        return contract.returncode
    print("OK: contrat SQL (idempotence, dépassement, commit, incertitude).")

    audit = run_psql(database_url, "", file=AUDIT_QUERY)
    if audit.returncode:
        sys.stderr.write(audit.stdout + audit.stderr)
        return audit.returncode
    print("OK: requête d’audit de rapprochement (lecture seule).")

    # Replaying the same idempotency key from independent sessions must
    # create one reservation and mark every other response as a replay.
    replay_account = "mission118-idempotency"
    replay_key = "m118-idempotency-duplicate-001"
    replay_sql = (
        "select reservation_status from public.papi_reserve_provider_quota("
        f"'{replay_key}', 'cloudflare', '{replay_account}', 'test-model', "
        "'PAPI-WORKER-REPLAY', 10, 100, date '2099-01-01');"
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        replay_results = list(pool.map(lambda _: run_psql(database_url, replay_sql), range(12)))
    replay_states = []
    for result in replay_results:
        if result.returncode:
            sys.stderr.write(result.stdout + result.stderr)
            return result.returncode
        replay_states.append(result.stdout.strip())
    if replay_states.count("reserved") != 1 or replay_states.count("reused_reserved") != 11:
        raise SystemExit(
            "ÉCHEC rejeu concurrent : attendu 1 réservation créée et 11 rejeux, "
            f"obtenu {replay_states!r}."
        )
    replay_verify = run_psql(database_url, (
        "select bucket.reserved_units || ',' || count(reservation.reservation_id) "
        "from public.papi_provider_daily_quotas as bucket "
        "join public.papi_provider_quota_reservations as reservation "
        "using (provider, account_ref, model, quota_day) "
        f"where bucket.provider='cloudflare' and bucket.account_ref='{replay_account}' "
        "and bucket.model='test-model' and bucket.quota_day=date '2099-01-01' "
        "group by bucket.reserved_units;"
    ))
    if replay_verify.returncode or replay_verify.stdout.strip() != "10,1":
        raise SystemExit(
            "ÉCHEC comptabilité du rejeu concurrent : "
            f"reçu {replay_verify.stdout.strip()!r}, attendu '10,1'. {replay_verify.stderr}"
        )
    print("OK: 12 sessions, même clé — 1 réservation créée, 11 rejeux, quota réservé=10/100.")

    for agents in (10, 20, 50):
        account = f"mission106-{agents}"
        sql_calls = []
        for index in range(agents):
            key = f"m106-{agents}-{index:03d}"
            worker = f"TEST-WORKER-{index:03d}"
            sql_calls.append(
                "select reservation_status from public.papi_reserve_provider_quota("
                f"'{key}', 'cloudflare', '{account}', 'test-model', '{worker}', "
                f"{ESTIMATE}, {DAILY_LIMIT}, date '{DAY}');"
            )

        def reserve(sql: str) -> tuple[bool, str]:
            result = run_psql(database_url, sql)
            if result.returncode == 0 and "reserved" in result.stdout:
                return True, result.stdout.strip()
            combined = result.stdout + result.stderr
            if "Provider daily quota exceeded" in combined:
                return False, "quota_exceeded"
            raise RuntimeError(f"Réservation en erreur inattendue: {combined}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=agents) as pool:
            outcomes = list(pool.map(reserve, sql_calls))

        accepted = sum(1 for success, _ in outcomes if success)
        rejected = agents - accepted
        expected_accepted = DAILY_LIMIT // ESTIMATE
        if accepted != expected_accepted or rejected != agents - expected_accepted:
            raise SystemExit(
                f"ÉCHEC {agents} agents: {accepted} acceptées, {rejected} refusées; "
                f"attendu {expected_accepted} acceptées."
            )

        verify_sql = (
            "select reserved_units || ',' || consumed_units || ',' || daily_limit "
            "from public.papi_provider_daily_quotas "
            f"where provider='cloudflare' and account_ref='{account}' "
            f"and model='test-model' and quota_day=date '{DAY}';"
        )
        verify = run_psql(database_url, verify_sql)
        expected = f"{DAILY_LIMIT},0,{DAILY_LIMIT}"
        if verify.returncode or verify.stdout.strip() != expected:
            raise SystemExit(
                f"ÉCHEC vérification {agents} agents: "
                f"reçu {verify.stdout.strip()!r}, attendu {expected!r}. {verify.stderr}"
            )
        print(f"OK: {agents} agents simultanés — {accepted} acceptées, "
              f"{rejected} refusées, quota réservé={DAILY_LIMIT}/{DAILY_LIMIT}.")

    print("SUCCÈS: aucune sur-réservation détectée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
