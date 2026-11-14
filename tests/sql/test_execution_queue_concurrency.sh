#!/usr/bin/env bash
set -euo pipefail

: "${PGHOST:?PGHOST is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGDATABASE:?PGDATABASE is required}"

psql_cmd=(psql -X -qAt -v ON_ERROR_STOP=1)
out_a="$(mktemp)"
out_b="$(mktemp)"
cleanup() {
  rm -f "$out_a" "$out_b"
}
trap cleanup EXIT

# Session A reserves one row and deliberately holds its transaction open.
# Session B starts while A still owns the row lock; SKIP LOCKED must give B
# the other job rather than block or return the same job.
"${psql_cmd[@]}" >"$out_a" <<'SQL' &
begin;
select (claim->>'id') || E'\t' || (claim->>'lease_token')
  from (select public.papi_claim_job('ci-concurrent-worker-a', gen_random_uuid(), 60) as claim) q;
select pg_sleep(3);
commit;
SQL
pid_a=$!

sleep 0.5
"${psql_cmd[@]}" >"$out_b" <<'SQL'
select (claim->>'id') || E'\t' || (claim->>'lease_token')
  from (select public.papi_claim_job('ci-concurrent-worker-b', gen_random_uuid(), 60) as claim) q;
SQL

wait "$pid_a"

claim_a="$(grep '^CI-CONCURRENT-JOB-' "$out_a" | tail -n 1)"
claim_b="$(grep '^CI-CONCURRENT-JOB-' "$out_b" | tail -n 1)"
if [[ -z "$claim_a" || -z "$claim_b" ]]; then
  echo "Concurrent claims did not both return a job" >&2
  cat "$out_a" "$out_b" >&2
  exit 1
fi

IFS=$'\t' read -r id_a token_a <<<"$claim_a"
IFS=$'\t' read -r id_b token_b <<<"$claim_b"
if [[ "$id_a" == "$id_b" ]]; then
  echo "Two concurrent workers received the same job: $id_a" >&2
  exit 1
fi
if [[ "$token_a" == "$token_b" ]]; then
  echo "Concurrent claims reused a lease token" >&2
  exit 1
fi
case "$id_a:$id_b" in
  *CI-CONCURRENT-JOB-A*CI-CONCURRENT-JOB-B*|*CI-CONCURRENT-JOB-B*CI-CONCURRENT-JOB-A*) ;;
  *)
    echo "Claims did not cover exactly the two concurrency fixtures: $id_a / $id_b" >&2
    exit 1
    ;;
esac

# Release both leases through their actual owners and fencing tokens.
"${psql_cmd[@]}" -v job_id="$id_a" -v lease_token="$token_a" \
  -c "select public.papi_complete_job(:'job_id', 'ci-concurrent-worker-a', :'lease_token'::uuid, '{\"concurrency_test\":true}'::jsonb) as completed" > /dev/null 2>&1 || true
"${psql_cmd[@]}" -v job_id="$id_b" -v lease_token="$token_b" \
  -c "select public.papi_complete_job(:'job_id', case when :'job_id' = 'CI-CONCURRENT-JOB-A' then 'ci-concurrent-worker-a' else 'ci-concurrent-worker-b' end, :'lease_token'::uuid, '{\"concurrency_test\":true}'::jsonb)" > /dev/null

echo "PASS: overlapping PostgreSQL sessions claimed distinct jobs with distinct lease tokens ($id_a, $id_b)"
