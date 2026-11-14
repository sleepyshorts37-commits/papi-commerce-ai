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


-- Stockage centralisé des snapshots PAPI AI WORKERS et reçus d'idempotence.
-- Les payloads sont des données métier non sensibles : aucun secret, OTP ou moyen
-- de paiement ne doit être transmis par le backend à cette fonction.
create table if not exists public.papi_worker_records (
    domain text not null check (domain in ('platform_candidate', 'human_handoff', 'profitability_result')),
    record_id text not null check (length(record_id) between 1 and 160),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    version bigint not null default 1 check (version >= 1),
    source_event_id text not null check (length(source_event_id) between 1 and 160),
    updated_at timestamptz not null default now(),
    primary key (domain, record_id)
);

create index if not exists papi_worker_records_updated_idx
    on public.papi_worker_records(domain, updated_at desc);

create table if not exists public.papi_worker_event_receipts (
    event_id text primary key,
    idempotency_key text not null unique check (length(idempotency_key) = 64),
    domain text not null check (domain in ('platform_candidate', 'human_handoff', 'profitability_result')),
    record_id text not null check (length(record_id) between 1 and 160),
    source_event_id text not null check (length(source_event_id) between 1 and 160),
    event_type text not null check (length(event_type) between 1 and 160),
    actor text not null check (length(actor) between 1 and 160),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    occurred_at timestamptz not null,
    record_version bigint not null check (record_version >= 1),
    received_at timestamptz not null default now()
);

create index if not exists papi_worker_event_record_idx
    on public.papi_worker_event_receipts(domain, record_id, occurred_at desc);

alter table public.papi_worker_records enable row level security;
alter table public.papi_worker_event_receipts enable row level security;

revoke all on public.papi_worker_records from public, anon, authenticated;
revoke all on public.papi_worker_event_receipts from public, anon, authenticated;
grant select, insert, update on public.papi_worker_records to service_role;
grant select, insert on public.papi_worker_event_receipts to service_role;

-- Écrit un snapshot et son reçu d'événement dans une seule transaction.
-- expected_version = 0 crée le record ; sinon la version doit correspondre.
-- Une nouvelle tentative identique renvoie duplicate=true sans réécrire le record.
create or replace function public.papi_sync_worker_record(
    p_domain text,
    p_record_id text,
    p_expected_version bigint,
    p_event_id text,
    p_idempotency_key text,
    p_source_event_id text,
    p_event_type text,
    p_actor text,
    p_payload jsonb,
    p_occurred_at timestamptz
) returns jsonb
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_receipt public.papi_worker_event_receipts%rowtype;
    v_new_version bigint;
begin
    if p_domain is null or p_domain not in ('platform_candidate', 'human_handoff', 'profitability_result')
       or p_record_id is null or length(trim(p_record_id)) not between 1 and 160
       or p_expected_version is null or p_expected_version < 0
       or p_event_id is null or length(trim(p_event_id)) not between 1 and 160
       or p_idempotency_key is null or p_idempotency_key !~ '^[0-9a-f]{64}$'
       or p_source_event_id is null or length(trim(p_source_event_id)) not between 1 and 160
       or p_event_type is null or length(trim(p_event_type)) not between 1 and 160
       or p_actor is null or length(trim(p_actor)) not between 1 and 160
       or p_payload is null or jsonb_typeof(p_payload) <> 'object'
       or p_occurred_at is null then
        raise exception 'Invalid worker sync event' using errcode = '22023';
    end if;

    -- Serialize retries sharing an idempotency key, including the first insert race.
    -- A hash collision only adds harmless contention; it cannot weaken uniqueness.
    perform pg_advisory_xact_lock(hashtextextended(p_idempotency_key, 0));

    select * into v_receipt
      from public.papi_worker_event_receipts
     where idempotency_key = p_idempotency_key
     for update;

    if found then
        if v_receipt.event_id is distinct from p_event_id
           or v_receipt.domain is distinct from p_domain
           or v_receipt.record_id is distinct from p_record_id
           or v_receipt.source_event_id is distinct from p_source_event_id
           or v_receipt.event_type is distinct from p_event_type
           or v_receipt.actor is distinct from p_actor
           or v_receipt.payload is distinct from p_payload
           or v_receipt.occurred_at is distinct from p_occurred_at then
            raise exception 'Idempotency key reused with different event content' using errcode = '22023';
        end if;
        return jsonb_build_object(
            'duplicate', true,
            'event_id', v_receipt.event_id,
            'record_version', v_receipt.record_version
        );
    end if;

    if p_expected_version = 0 then
        insert into public.papi_worker_records(
            domain, record_id, payload, version, source_event_id, updated_at
        ) values (
            p_domain, p_record_id, p_payload, 1, p_source_event_id, now()
        )
        on conflict (domain, record_id) do nothing
        returning version into v_new_version;
    else
        update public.papi_worker_records
           set payload = p_payload,
               version = version + 1,
               source_event_id = p_source_event_id,
               updated_at = now()
         where domain = p_domain
           and record_id = p_record_id
           and version = p_expected_version
        returning version into v_new_version;
    end if;

    if v_new_version is null then
        raise exception 'Worker record version conflict or record not found' using errcode = '40001';
    end if;

    insert into public.papi_worker_event_receipts(
        event_id, idempotency_key, domain, record_id, source_event_id,
        event_type, actor, payload, occurred_at, record_version
    ) values (
        p_event_id, p_idempotency_key, p_domain, p_record_id, p_source_event_id,
        p_event_type, p_actor, p_payload, p_occurred_at, v_new_version
    );

    insert into public.papi_audit_events(
        event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
        p_event_id, p_occurred_at, p_actor, p_event_type, 'worker_' || p_domain,
        p_record_id,
        jsonb_build_object(
            'record_version', v_new_version,
            'source_event_id', p_source_event_id,
            'idempotency_key', p_idempotency_key,
            'payload', p_payload
        )
    );

    return jsonb_build_object(
        'duplicate', false,
        'event_id', p_event_id,
        'record_version', v_new_version
    );
end;
$$;

revoke all on function public.papi_sync_worker_record(
    text, text, bigint, text, text, text, text, text, jsonb, timestamptz
) from public, anon, authenticated;
grant execute on function public.papi_sync_worker_record(
    text, text, bigint, text, text, text, text, text, jsonb, timestamptz
) to service_role;
