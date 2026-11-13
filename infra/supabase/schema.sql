-- PAPI COMMERCE AI — Supabase / PostgreSQL
-- Exécuter dans l'éditeur SQL du projet Supabase.
-- Les tables ne sont accessibles ni à anon ni à authenticated.
-- Le backend doit utiliser une clé serveur conservée uniquement dans ses secrets.

create table if not exists public.papi_tasks (
    id text primary key,
    task jsonb not null check (jsonb_typeof(task) = 'object'),
    version bigint not null default 1 check (version >= 1),
    updated_at timestamptz not null default now()
);

create table if not exists public.papi_audit_events (
    event_id text primary key,
    occurred_at timestamptz not null,
    actor text not null,
    action text not null,
    entity_type text not null,
    entity_id text not null,
    details jsonb not null default '{}'::jsonb check (jsonb_typeof(details) = 'object')
);

create index if not exists papi_tasks_updated_at_idx on public.papi_tasks(updated_at);
create index if not exists papi_audit_entity_idx on public.papi_audit_events(entity_type, entity_id);

alter table public.papi_tasks enable row level security;
alter table public.papi_audit_events enable row level security;

revoke all on public.papi_tasks from anon, authenticated;
revoke all on public.papi_audit_events from anon, authenticated;
grant select, insert, update on public.papi_tasks to service_role;
grant select, insert on public.papi_audit_events to service_role;

-- Une transition et son événement sont validés ou annulés ensemble.
-- Le contrôle de version empêche deux agents d'écraser une modification concurrente.
create or replace function public.papi_commit_task_change(
    p_task_id text,
    p_expected_version bigint,
    p_task jsonb,
    p_event jsonb
) returns bigint
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_new_version bigint;
begin
    if p_task_id is null or length(trim(p_task_id)) = 0
       or jsonb_typeof(p_task) <> 'object'
       or p_task->>'id' is distinct from p_task_id
       or jsonb_typeof(p_event) <> 'object'
       or p_event->>'entity_type' is distinct from 'task'
       or p_event->>'entity_id' is distinct from p_task_id
       or p_event->>'event_id' is null
       or p_event->>'occurred_at' is null
       or p_event->>'actor' is null
       or p_event->>'action' is null
       or jsonb_typeof(p_event->'details') <> 'object'
       or p_expected_version < 1 then
        raise exception 'Invalid task change payload' using errcode = '22023';
    end if;

    update public.papi_tasks
       set task = p_task,
           version = version + 1,
           updated_at = now()
     where id = p_task_id
       and version = p_expected_version
    returning version into v_new_version;

    if v_new_version is null then
        raise exception 'Task version conflict or task not found' using errcode = '40001';
    end if;

    insert into public.papi_audit_events (
        event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
        p_event->>'event_id',
        (p_event->>'occurred_at')::timestamptz,
        p_event->>'actor',
        p_event->>'action',
        p_event->>'entity_type',
        p_event->>'entity_id',
        p_event->'details'
    );

    return v_new_version;
end;
$$;

revoke all on function public.papi_commit_task_change(text, bigint, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.papi_commit_task_change(text, bigint, jsonb, jsonb) to service_role;

-- File d'exécution : réservation exclusive avec bail et reprise après expiration.
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
alter table public.papi_jobs add column if not exists agent_identity jsonb check (agent_identity is null or jsonb_typeof(agent_identity) = 'object');
create index if not exists papi_jobs_ready_idx on public.papi_jobs(status, available_at, created_at);
alter table public.papi_jobs enable row level security;
revoke all on public.papi_jobs from anon, authenticated;
grant select, insert, update on public.papi_jobs to service_role;

create or replace function public.papi_claim_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_job public.papi_jobs%rowtype;
begin
    -- Une réservation qui expire à sa dernière tentative est terminale : ne pas la laisser bloquée.
    update public.papi_jobs
       set status = 'failed', last_error_code = 'lease_expired_max_attempts',
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where status = 'running' and lease_until < now() and attempts >= max_attempts;

    if p_worker_id is null or length(trim(p_worker_id)) = 0 or length(p_worker_id) > 120
       or p_lease_token is null or p_lease_seconds < 15 or p_lease_seconds > 900 then
        raise exception 'Invalid worker lease request' using errcode = '22023';
    end if;
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
       set status = 'running',
           attempts = attempts + 1,
           lease_owner = p_worker_id,
           lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;
    return jsonb_build_object(
        'id', v_job.id, 'task_id', v_job.task_id, 'handler', v_job.handler,
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity, 'attempts', v_job.attempts,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
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
declare
    v_job public.papi_jobs%rowtype;
    v_status text;
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
    if v_job.attempts >= v_job.max_attempts then
        v_status := 'failed';
    else
        v_status := 'retry';
    end if;
    update public.papi_jobs
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => least(3600, 15 * power(2, attempts - 1)::integer))
             else available_at end,
           last_error_code = p_error_code,
           updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id;
    return v_status;
end;
$$;

revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_complete_job(text, text, uuid, jsonb) from public, anon, authenticated;
revoke all on function public.papi_fail_job(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
grant execute on function public.papi_complete_job(text, text, uuid, jsonb) to service_role;
grant execute on function public.papi_fail_job(text, text, uuid, text) to service_role;

-- Identités Ed25519 partagées entre workers (migration additive).
-- Les clés privées ne sont JAMAIS stockées dans Supabase.
create table if not exists public.papi_agent_public_keys (
    agent_id text not null check (agent_id ~ '^[A-Za-z0-9_-]{1,100}$'),
    key_version integer not null check (key_version >= 1),
    public_key_hex text not null check (public_key_hex ~ '^[0-9a-f]{64}$'),
    status text not null default 'active' check (status in ('active', 'revoked')),
    created_at timestamptz not null default now(),
    revoked_at timestamptz,
    primary key (agent_id, key_version),
    check ((status = 'revoked') = (revoked_at is not null))
);
create unique index if not exists papi_agent_one_active_key_idx
    on public.papi_agent_public_keys(agent_id) where status = 'active';

create table if not exists public.papi_agent_used_nonces (
    agent_id text not null,
    nonce text not null check (length(nonce) between 16 and 128),
    expires_at timestamptz not null,
    consumed_at timestamptz not null default now(),
    primary key (agent_id, nonce)
);
create index if not exists papi_agent_used_nonces_expiry_idx
    on public.papi_agent_used_nonces(expires_at);

alter table public.papi_agent_public_keys enable row level security;
alter table public.papi_agent_used_nonces enable row level security;
revoke all on public.papi_agent_public_keys from public, anon, authenticated;
revoke all on public.papi_agent_used_nonces from public, anon, authenticated;
grant select, insert, update on public.papi_agent_public_keys to service_role;
grant select, insert, delete on public.papi_agent_used_nonces to service_role;

-- L'insertion atomique garantit qu'un nonce ne peut être consommé que par un worker.
create or replace function public.papi_consume_agent_nonce(
    p_agent_id text, p_nonce text, p_expires_at timestamptz
) returns boolean
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare v_inserted integer;
begin
    if p_agent_id is null or p_agent_id !~ '^[A-Za-z0-9_-]{1,100}$'
       or p_nonce is null or length(p_nonce) < 16 or length(p_nonce) > 128
       or p_expires_at is null or p_expires_at <= now()
       or p_expires_at > now() + interval '10 minutes' then
        raise exception 'Invalid agent nonce' using errcode = '22023';
    end if;

    delete from public.papi_agent_used_nonces where expires_at < now();

    insert into public.papi_agent_used_nonces(agent_id, nonce, expires_at)
    values (p_agent_id, p_nonce, p_expires_at)
    on conflict (agent_id, nonce) do nothing;

    get diagnostics v_inserted = row_count;
    return v_inserted = 1;
end;
$$;
revoke all on function public.papi_consume_agent_nonce(text, text, timestamptz)
    from public, anon, authenticated;
grant execute on function public.papi_consume_agent_nonce(text, text, timestamptz)
    to service_role;


-- Durable attempt history (kept in sync with migrations).
-- PAPI: durable identity and history for every effective job reservation.
-- Additive and safe for existing jobs. Existing history is necessarily reconstructed
-- as one legacy snapshot because the old schema retained only the attempts counter.

alter table public.papi_jobs
    add column if not exists current_attempt_id uuid;

create table if not exists public.papi_job_attempts (
    attempt_id uuid primary key,
    job_id text not null references public.papi_jobs(id) on delete restrict,
    attempt_number integer not null check (attempt_number > 0),
    worker_id text,
    lease_token uuid,
    status text not null check (status in ('running', 'retry', 'completed', 'failed', 'lease_expired')),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    error_code text,
    is_legacy boolean not null default false,
    unique (job_id, attempt_number),
    check ((status = 'running') = (finished_at is null))
);

-- Preserve the latest known attempt for jobs created before this migration.
with legacy as (
    select id as job_id, attempts as attempt_number, gen_random_uuid() as attempt_id,
           coalesce(lease_owner, 'legacy-unknown') as worker_id,
           lease_token,
           case
             when status = 'running' then 'running'
             when status = 'done' then 'completed'
             when status = 'failed' then 'failed'
             else 'retry'
           end as attempt_status,
           case when status = 'running' then null else updated_at end as finished_at,
           updated_at as started_at
      from public.papi_jobs
     where attempts > 0
)
insert into public.papi_job_attempts
    (attempt_id, job_id, attempt_number, worker_id, lease_token, status, started_at, finished_at, is_legacy)
select attempt_id, job_id, attempt_number, worker_id, lease_token, attempt_status,
       started_at, finished_at, true
  from legacy
on conflict (job_id, attempt_number) do nothing;

update public.papi_jobs j
   set current_attempt_id = a.attempt_id
  from public.papi_job_attempts a
 where a.job_id = j.id
   and a.attempt_number = j.attempts
   and j.current_attempt_id is null;

do $attempt_fk$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'papi_jobs_current_attempt_fk'
          and conrelid = 'public.papi_jobs'::regclass
    ) then
        alter table public.papi_jobs
            add constraint papi_jobs_current_attempt_fk
            foreign key (current_attempt_id)
            references public.papi_job_attempts(attempt_id)
            deferrable initially deferred;
    end if;
end;
$attempt_fk$;

create index if not exists papi_job_attempts_job_started_idx
    on public.papi_job_attempts(job_id, started_at desc);
create index if not exists papi_job_attempts_status_idx
    on public.papi_job_attempts(status, started_at);

alter table public.papi_job_attempts enable row level security;
revoke all on public.papi_job_attempts from public, anon, authenticated;
grant select, insert, update on public.papi_job_attempts to service_role;

create or replace function public.papi_sync_job_attempt()
returns trigger
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
begin
    if old.current_attempt_id is not null
       and new.current_attempt_id is distinct from old.current_attempt_id then
        update public.papi_job_attempts
           set status = 'lease_expired', finished_at = coalesce(finished_at, now()),
               error_code = coalesce(error_code, 'lease_replaced')
         where attempt_id = old.current_attempt_id and status = 'running';
    elsif old.status = 'running' and new.status in ('done', 'retry', 'failed') then
        update public.papi_job_attempts
           set status = case new.status
                          when 'done' then 'completed'
                          when 'retry' then 'retry'
                          else 'failed'
                        end,
               finished_at = coalesce(finished_at, now()),
               error_code = case when new.status = 'failed' then new.last_error_code else error_code end
         where attempt_id = old.current_attempt_id and status = 'running';
    end if;
    return new;
end;
$$;

drop trigger if exists papi_jobs_sync_attempt on public.papi_jobs;
create trigger papi_jobs_sync_attempt
after update of status, current_attempt_id on public.papi_jobs
for each row execute function public.papi_sync_job_attempt();

create or replace function public.papi_claim_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare
    v_job public.papi_jobs%rowtype;
    v_attempt_id uuid;
    v_attempt_number integer;
begin
    update public.papi_jobs
       set status = 'failed', last_error_code = 'lease_expired_max_attempts',
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where status = 'running' and lease_until < now() and attempts >= max_attempts;

    if p_worker_id is null or length(trim(p_worker_id)) = 0 or length(p_worker_id) > 120
       or p_lease_token is null or p_lease_seconds is null
       or p_lease_seconds < 15 or p_lease_seconds > 900 then
        raise exception 'Invalid worker lease request' using errcode = '22023';
    end if;

    select * into v_job
      from public.papi_jobs
     where attempts < max_attempts
       and ((status in ('queued', 'retry') and available_at <= now())
         or (status = 'running' and lease_until < now()))
     order by available_at, created_at
     for update skip locked
     limit 1;
    if not found then return null; end if;

    v_attempt_id := gen_random_uuid();
    v_attempt_number := v_job.attempts + 1;

    insert into public.papi_job_attempts
        (attempt_id, job_id, attempt_number, worker_id, lease_token, status)
    values
        (v_attempt_id, v_job.id, v_attempt_number, p_worker_id, p_lease_token, 'running');

    update public.papi_jobs
       set status = 'running',
           attempts = v_attempt_number,
           current_attempt_id = v_attempt_id,
           lease_owner = p_worker_id,
           lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;

    return jsonb_build_object(
        'id', v_job.id, 'task_id', v_job.task_id, 'handler', v_job.handler,
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity,
        'attempts', v_job.attempts, 'attempt_id', v_job.current_attempt_id,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
end;
$$;

revoke all on function public.papi_sync_job_attempt() from public, anon, authenticated;
revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
