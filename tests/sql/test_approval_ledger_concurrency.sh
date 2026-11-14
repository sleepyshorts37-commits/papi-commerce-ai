#!/usr/bin/env bash
set -euo pipefail

: "${PGHOST:?PGHOST is required}"
: "${PGPORT:?PGPORT is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGDATABASE:?PGDATABASE is required}"

suffix="$$"
task_id="TASK-M26-RACE-${suffix}"
approval_id="APR-M26-RACE-${suffix}"
out_a="$(mktemp)"
out_b="$(mktemp)"
trap 'rm -f "$out_a" "$out_b"' EXIT

psql -X -v ON_ERROR_STOP=1 -q \
  -c "insert into public.papi_tasks(id, task, version) values ('$task_id', jsonb_build_object('id', '$task_id', 'status', 'in_progress'), 1);"
psql -X -v ON_ERROR_STOP=1 -q \
  -c "select public.papi_issue_approval('$approval_id', '$task_id', 'external.email.send', 'external_communication', 'owner-race', now(), now() + interval '5 minutes');"

consume_sql="select public.papi_consume_approval('$approval_id', '$task_id', 'external.email.send', 'external_communication', 'agent-race');"
psql -X -A -t -v ON_ERROR_STOP=1 -c "$consume_sql" >"$out_a" &
pid_a=$!
psql -X -A -t -v ON_ERROR_STOP=1 -c "$consume_sql" >"$out_b" &
pid_b=$!
wait "$pid_a"
wait "$pid_b"

result_a="$(tr -d '[:space:]' <"$out_a")"
result_b="$(tr -d '[:space:]' <"$out_b")"
if ! { [[ "$result_a" == "t" && "$result_b" == "f" ]] || [[ "$result_a" == "f" && "$result_b" == "t" ]]; }; then
  echo "Expected exactly one successful concurrent approval consumption; got '$result_a' and '$result_b'" >&2
  exit 1
fi

echo "PASS: exactly one concurrent consumer succeeded."
