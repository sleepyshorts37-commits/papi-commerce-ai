#!/usr/bin/env bash
set -euo pipefail
: "${PGHOST:?PGHOST is required}"
: "${PGPORT:?PGPORT is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGDATABASE:?PGDATABASE is required}"

suffix="$$"
key="ci-m27-race-${suffix}"
one="$(mktemp)"
two="$(mktemp)"
trap 'rm -f "$one" "$two"' EXIT

psql -X -q -v ON_ERROR_STOP=1 -c "select public.papi_enqueue_outbox('$key', 'test.race', 'RACE-$suffix', '{}'::jsonb, 2);" >/dev/null
sql="select case when public.papi_claim_outbox('race-worker', gen_random_uuid(), 60) is not null then 't' else 'f' end;"
psql -X -A -t -v ON_ERROR_STOP=1 -c "$sql" >"$one" &
pid_one=$!
psql -X -A -t -v ON_ERROR_STOP=1 -c "$sql" >"$two" &
pid_two=$!
wait "$pid_one"
wait "$pid_two"
a="$(tr -d '[:space:]' <"$one")"
b="$(tr -d '[:space:]' <"$two")"
if ! { [[ "$a" == "t" && "$b" == "f" ]] || [[ "$a" == "f" && "$b" == "t" ]]; }; then
  echo "Expected one concurrent claim and one empty result; received '$a' and '$b'" >&2
  exit 1
fi
echo "PASS: only one concurrent worker claimed the same outbox item."
