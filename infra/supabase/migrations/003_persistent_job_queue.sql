-- PAPI TASK QUEUE 1.7 — file persistante avec réservation transactionnelle.
-- À appliquer après schema.sql / migration 002. Les workers ne sont pas activés par cette migration.

create table if not exists public.papi_jobs (
    id text primary key,
    task_id text not null references public.papi_tasks(id) on delete restrict,
    handler text not null check (length(handler) between 1 and 100),
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    agent_identity jsonb check (agent_identity is null or jsonb_typeof(agent_identity) = 'object'),
    idempotency_key text not null unique,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'retry', 'done', 'failed')),
    attempts integer not null default 0 check (attempts >= 0),
    max_attempts integer not null default 5 check (max_attempts between 1 and 10),
    available_at timestamptz not null default now(),
    lease_owner text,
    lease_token uuid,
    lease_until timestamptz,
    last_error_code text,
    result jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check ((status = 'running') = (lease_owner is not null and lease_token is not null and lease_until is not null))
);
alter table public.papi_jobs add column if not exists agent_identity jsonb
    check (agent_identity is null or jsonb_typeof(agent_identity) = 'object');
create index if not exists papi_jobs_ready_idx on public.papi_jobs(status, available_at, created_at);
alter table public.papi_jobs enable row level security;
revoke all on public.papi_jobs from public, anon, authenticated;
grant select, insert, update on public.papi_jobs to service_role;

create or replace function public.papi_claim_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_job public.papi_jobs%rowtype;
begin
    if p_worker_id is null or length(trim(p_worker_id)) = 0 or length(p_worker_id) > 120
       or p_lease_token is null or p_lease_seconds is null
       or p_lease_seconds < 15 or p_lease_seconds > 900 then
        raise exception 'Invalid worker lease request' using errcode = '22023';
    end if;

    update public.papi_jobs
       set status = 'failed', last_error_code = 'lease_expired_max_attempts',
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where status = 'running' and lease_until < now() and attempts >= max_attempts;

    select * into v_job
      from public.papi_jobs
     where attempts < max_attempts
       and ((status in ('queued', 'retry') and available_at <= now())
         or (status = 'running' and lease_until < now()))
     order by available_at, created_at
     for update skip locked
     limit 1;
    if not found then return null; end if;

    update public.papi_jobs
       set status = 'running', attempts = attempts + 1,
           lease_owner = p_worker_id, lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;

    return jsonb_build_object(
        'id', v_job.id, 'task_id', v_job.task_id, 'handler', v_job.handler,
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity,
        'attempts', v_job.attempts, 'lease_token', v_job.lease_token,
        'lease_until', v_job.lease_until
    );
end;
$$;

create or replace function public.papi_heartbeat_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns boolean
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_count integer;
begin
    if p_lease_seconds is null or p_lease_seconds < 15 or p_lease_seconds > 900 then
        raise exception 'Invalid heartbeat duration' using errcode = '22023';
    end if;
    update public.papi_jobs
       set lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now();
    get diagnostics v_count = row_count;
    return v_count = 1;
end;
$$;

create or replace function public.papi_complete_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_result jsonb default '{}'::jsonb
) returns boolean
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_count integer;
begin
    if jsonb_typeof(p_result) <> 'object' then
        raise exception 'Invalid result object' using errcode = '22023';
    end if;
    update public.papi_jobs
       set status = 'done', result = p_result, updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now();
    get diagnostics v_count = row_count;
    return v_count = 1;
end;
$$;

create or replace function public.papi_fail_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_error_code text
) returns text
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_job public.papi_jobs%rowtype; v_status text;
begin
    if p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}$' then
        raise exception 'Invalid error code' using errcode = '22023';
    end if;
    select * into v_job from public.papi_jobs
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now()
     for update;
    if not found then
        raise exception 'Job lease lost or expired' using errcode = '40001';
    end if;
    if v_job.attempts >= v_job.max_attempts then v_status := 'failed';
    else v_status := 'retry'; end if;
    update public.papi_jobs
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => least(3600, 15 * power(2, attempts - 1)::integer))
             else available_at end,
           last_error_code = p_error_code, updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id;
    return v_status;
end;
$$;

revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_heartbeat_job(text, text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_complete_job(text, text, uuid, jsonb) from public, anon, authenticated;
revoke all on function public.papi_fail_job(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
grant execute on function public.papi_heartbeat_job(text, text, uuid, integer) to service_role;
grant execute on function public.papi_complete_job(text, text, uuid, jsonb) to service_role;
grant execute on function public.papi_fail_job(text, text, uuid, text) to service_role;
