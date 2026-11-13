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
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity,
        'attempts', v_job.attempts, 'max_attempts', v_job.max_attempts,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
end;
$$;

-- Renouvelle un bail uniquement s'il est encore valide et appartient au worker/token.
create or replace function public.papi_renew_job_lease(
    p_job_id text, p_worker_id text, p_lease_token uuid,
    p_lease_seconds integer default 900
) returns boolean
language plpgsql security invoker
set search_path = public, pg_temp
as $lease$
declare v_count integer;
begin
    if p_job_id is null or length(trim(p_job_id)) = 0
       or p_worker_id is null or length(trim(p_worker_id)) = 0
       or length(p_worker_id) > 120 or p_lease_token is null
       or p_lease_seconds is null or p_lease_seconds < 15
       or p_lease_seconds > 900 then
        raise exception 'Invalid lease renewal request' using errcode = '22023';
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
$lease$;

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

-- Versioned retry contract: the client supplies a bounded policy decision,
-- while PostgreSQL re-checks the durable attempt ceiling and lease ownership.
create or replace function public.papi_fail_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_error_code text,
    p_retry_allowed boolean, p_retry_delay_seconds integer
) returns text
language plpgsql security invoker
set search_path = public, pg_temp
as $retry$
declare
    v_job public.papi_jobs%rowtype;
    v_status text;
begin
    if p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}
revoke all on function public.papi_renew_job_lease(text, text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_complete_job(text, text, uuid, jsonb) from public, anon, authenticated;
revoke all on function public.papi_fail_job(text, text, uuid, text) from public, anon, authenticated;
revoke all on function public.papi_fail_job(text, text, uuid, text, boolean, integer) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
grant execute on function public.papi_renew_job_lease(text, text, uuid, integer) to service_role;
grant execute on function public.papi_complete_job(text, text, uuid, jsonb) to service_role;
grant execute on function public.papi_fail_job(text, text, uuid, text) to service_role;
grant execute on function public.papi_fail_job(text, text, uuid, text, boolean, integer) to service_role;

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


-- External audit checkpoint witness. Only signed checkpoint envelopes are stored;
-- raw local audit events and business payloads are never copied here.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.papi_audit_anchor_records (
    journal_id text not null check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    record_digest text not null check (record_digest ~ '^[0-9a-f]{64}$'),
    canonical_record text not null,
    created_at timestamptz not null default now(),
    primary key (journal_id, record_digest)
);

create table if not exists public.papi_audit_anchor_heads (
    journal_id text primary key check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    latest_record_digest text not null check (latest_record_digest ~ '^[0-9a-f]{64}$'),
    sequence bigint not null check (sequence >= 0),
    head_hash text not null check (head_hash ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz not null default now()
);

alter table public.papi_audit_anchor_records enable row level security;
alter table public.papi_audit_anchor_heads enable row level security;
revoke all on public.papi_audit_anchor_records from public, anon, authenticated;
revoke all on public.papi_audit_anchor_heads from public, anon, authenticated;
grant select, insert on public.papi_audit_anchor_records to service_role;
grant select on public.papi_audit_anchor_heads to service_role;

create or replace function public.papi_reject_audit_anchor_record_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $papi$
begin
    raise exception 'Audit anchor records are immutable' using errcode = '55000';
end;
$papi$;

drop trigger if exists papi_audit_anchor_records_immutable
    on public.papi_audit_anchor_records;
create trigger papi_audit_anchor_records_immutable
    before update or delete on public.papi_audit_anchor_records
    for each row execute function public.papi_reject_audit_anchor_record_mutation();

-- SECURITY DEFINER: keep pg_catalog first, qualify the extension digest function,
-- and never rely on an untrusted schema shadowing built-ins or helper functions.
create or replace function public.papi_advance_audit_anchor(
    p_journal_id text,
    p_expected_digest text,
    p_new_digest text
) returns boolean
language plpgsql
security definer
set search_path = pg_catalog, public, extensions, pg_temp
as $papi$
declare
    v_canonical text;
    v_record jsonb;
    v_checkpoint jsonb;
    v_sequence bigint;
    v_head_hash text;
    v_previous_digest text;
    v_key_id text;
    v_signature text;
    v_current public.papi_audit_anchor_heads%rowtype;
begin
    if p_journal_id is null or pg_catalog.length(p_journal_id) not between 1 and 120
       or p_journal_id ~ '[^A-Za-z0-9_.:-]'
       or p_new_digest is null or pg_catalog.length(p_new_digest) <> 64
       or p_new_digest ~ '[^0-9a-f]'
       or (p_expected_digest is not null and (
           pg_catalog.length(p_expected_digest) <> 64
           or p_expected_digest ~ '[^0-9a-f]'
       )) then
        raise exception 'Invalid audit anchor pointer' using errcode = '22023';
    end if;

    select canonical_record into v_canonical
      from public.papi_audit_anchor_records
     where journal_id = p_journal_id and record_digest = p_new_digest;
    if not found then
        raise exception 'Audit anchor record not found' using errcode = '22023';
    end if;
    if pg_catalog.encode(
        extensions.digest(pg_catalog.convert_to(v_canonical, 'UTF8'), 'sha256'),
        'hex'
    ) <> p_new_digest then
        raise exception 'Audit anchor record digest mismatch' using errcode = '22023';
    end if;

    begin
        v_record := v_canonical::jsonb;
        if pg_catalog.jsonb_typeof(v_record) <> 'object' then
            raise exception 'record must be an object';
        end if;
        if not (v_record ?& array['schema_version', 'journal_id', 'checkpoint', 'previous_record_digest', 'key_id', 'signature']) then
            raise exception 'record is missing required fields';
        end if;
        if (v_record - array[
            'schema_version', 'journal_id', 'checkpoint',
            'previous_record_digest', 'key_id', 'signature'
        ]) <> '{}'::jsonb then
            raise exception 'record contains unknown fields';
        end if;
        if pg_catalog.jsonb_typeof(v_record->'schema_version') <> 'number'
           or (v_record->>'schema_version')::integer <> 1 then
            raise exception 'unsupported record schema';
        end if;
        if v_record->>'journal_id' is distinct from p_journal_id then
            raise exception 'journal mismatch';
        end if;

        v_checkpoint := v_record->'checkpoint';
        if pg_catalog.jsonb_typeof(v_checkpoint) <> 'object'
           or not (v_checkpoint ?& array['schema_version', 'sequence', 'head_hash'])
           or (v_checkpoint - array['schema_version', 'sequence', 'head_hash']) <> '{}'::jsonb
           or pg_catalog.jsonb_typeof(v_checkpoint->'schema_version') <> 'number'
           or (v_checkpoint->>'schema_version')::integer <> 1
           or pg_catalog.jsonb_typeof(v_checkpoint->'sequence') <> 'number'
           or (v_checkpoint->>'sequence')::numeric < 0
           or (v_checkpoint->>'sequence')::numeric <> pg_catalog.trunc((v_checkpoint->>'sequence')::numeric)
 then
            raise exception 'invalid checkpoint envelope';
        end if;
        v_sequence := (v_checkpoint->>'sequence')::bigint;
        v_head_hash := v_checkpoint->>'head_hash';
        v_previous_digest := v_record->>'previous_record_digest';
        v_key_id := v_record->>'key_id';
        v_signature := v_record->>'signature';
    exception when others then
        raise exception 'Malformed audit anchor record' using errcode = '22023';
    end;

    if v_sequence < 0
       or v_head_hash is null or pg_catalog.length(v_head_hash) <> 64 or v_head_hash ~ '[^0-9a-f]'
       or (v_previous_digest is not null and (pg_catalog.length(v_previous_digest) <> 64 or v_previous_digest ~ '[^0-9a-f]'))
       or v_previous_digest is distinct from p_expected_digest
       or v_key_id is null or pg_catalog.length(v_key_id) not between 1 and 120 or v_key_id ~ '[^A-Za-z0-9_.:-]'

       or v_signature is null or pg_catalog.length(v_signature) = 0
       or pg_catalog.length(v_signature) > 2048 then
        raise exception 'Audit anchor record fields do not match pointer' using errcode = '22023';
    end if;

    -- Genesis insert; ON CONFLICT handles two concurrent first publishers.
    if p_expected_digest is null then
        insert into public.papi_audit_anchor_heads(
            journal_id, latest_record_digest, sequence, head_hash
        ) values (p_journal_id, p_new_digest, v_sequence, v_head_hash)
        on conflict (journal_id) do nothing;
        if found then
            return true;
        end if;
    end if;

    select * into v_current
      from public.papi_audit_anchor_heads
     where journal_id = p_journal_id
     for update;

    if not found then
        return false;
    end if;
    if v_current.latest_record_digest = p_new_digest then
        return v_current.sequence = v_sequence and v_current.head_hash = v_head_hash;
    end if;
    if v_current.latest_record_digest is distinct from p_expected_digest then
        return false;
    end if;
    if v_sequence <= v_current.sequence then
        raise exception 'Audit anchor sequence must increase' using errcode = '22023';
    end if;

    update public.papi_audit_anchor_heads
       set latest_record_digest = p_new_digest,
           sequence = v_sequence,
           head_hash = v_head_hash,
           updated_at = pg_catalog.now()
     where journal_id = p_journal_id;
    return true;
end;
$papi$;

revoke all on function public.papi_reject_audit_anchor_record_mutation() from public, anon, authenticated;
revoke all on function public.papi_advance_audit_anchor(text, text, text) from public, anon, authenticated;
grant execute on function public.papi_advance_audit_anchor(text, text, text) to service_role;

       or p_retry_allowed is null
       or p_retry_delay_seconds is null
       or p_retry_delay_seconds < 0 or p_retry_delay_seconds > 3600
       or (not p_retry_allowed and p_retry_delay_seconds <> 0)
       or (p_retry_allowed and p_error_code not in (
           'temporarily_unavailable', 'rate_limited',
           'connection_reset', 'service_timeout'
       )) then
        raise exception 'Invalid retry decision' using errcode = '22023';
    end if;

    select * into v_job from public.papi_jobs
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now()
     for update;
    if not found then
        raise exception 'Job lease lost or expired' using errcode = '40001';
    end if;

    if p_retry_allowed and v_job.attempts < v_job.max_attempts then
        v_status := 'retry';
    else
        v_status := 'failed';
    end if;

    update public.papi_jobs
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => p_retry_delay_seconds)
             else available_at end,
           last_error_code = p_error_code,
           updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id;
    return v_status;
end;
$retry$;

revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_renew_job_lease(text, text, uuid, integer) from public, anon, authenticated;
revoke all on function public.papi_complete_job(text, text, uuid, jsonb) from public, anon, authenticated;
revoke all on function public.papi_fail_job(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
grant execute on function public.papi_renew_job_lease(text, text, uuid, integer) to service_role;
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


-- External audit checkpoint witness. Only signed checkpoint envelopes are stored;
-- raw local audit events and business payloads are never copied here.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.papi_audit_anchor_records (
    journal_id text not null check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    record_digest text not null check (record_digest ~ '^[0-9a-f]{64}$'),
    canonical_record text not null,
    created_at timestamptz not null default now(),
    primary key (journal_id, record_digest)
);

create table if not exists public.papi_audit_anchor_heads (
    journal_id text primary key check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    latest_record_digest text not null check (latest_record_digest ~ '^[0-9a-f]{64}$'),
    sequence bigint not null check (sequence >= 0),
    head_hash text not null check (head_hash ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz not null default now()
);

alter table public.papi_audit_anchor_records enable row level security;
alter table public.papi_audit_anchor_heads enable row level security;
revoke all on public.papi_audit_anchor_records from public, anon, authenticated;
revoke all on public.papi_audit_anchor_heads from public, anon, authenticated;
grant select, insert on public.papi_audit_anchor_records to service_role;
grant select on public.papi_audit_anchor_heads to service_role;

create or replace function public.papi_reject_audit_anchor_record_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $papi$
begin
    raise exception 'Audit anchor records are immutable' using errcode = '55000';
end;
$papi$;

drop trigger if exists papi_audit_anchor_records_immutable
    on public.papi_audit_anchor_records;
create trigger papi_audit_anchor_records_immutable
    before update or delete on public.papi_audit_anchor_records
    for each row execute function public.papi_reject_audit_anchor_record_mutation();

-- SECURITY DEFINER: keep pg_catalog first, qualify the extension digest function,
-- and never rely on an untrusted schema shadowing built-ins or helper functions.
create or replace function public.papi_advance_audit_anchor(
    p_journal_id text,
    p_expected_digest text,
    p_new_digest text
) returns boolean
language plpgsql
security definer
set search_path = pg_catalog, public, extensions, pg_temp
as $papi$
declare
    v_canonical text;
    v_record jsonb;
    v_checkpoint jsonb;
    v_sequence bigint;
    v_head_hash text;
    v_previous_digest text;
    v_key_id text;
    v_signature text;
    v_current public.papi_audit_anchor_heads%rowtype;
begin
    if p_journal_id is null or pg_catalog.length(p_journal_id) not between 1 and 120
       or p_journal_id ~ '[^A-Za-z0-9_.:-]'
       or p_new_digest is null or pg_catalog.length(p_new_digest) <> 64
       or p_new_digest ~ '[^0-9a-f]'
       or (p_expected_digest is not null and (
           pg_catalog.length(p_expected_digest) <> 64
           or p_expected_digest ~ '[^0-9a-f]'
       )) then
        raise exception 'Invalid audit anchor pointer' using errcode = '22023';
    end if;

    select canonical_record into v_canonical
      from public.papi_audit_anchor_records
     where journal_id = p_journal_id and record_digest = p_new_digest;
    if not found then
        raise exception 'Audit anchor record not found' using errcode = '22023';
    end if;
    if pg_catalog.encode(
        extensions.digest(pg_catalog.convert_to(v_canonical, 'UTF8'), 'sha256'),
        'hex'
    ) <> p_new_digest then
        raise exception 'Audit anchor record digest mismatch' using errcode = '22023';
    end if;

    begin
        v_record := v_canonical::jsonb;
        if pg_catalog.jsonb_typeof(v_record) <> 'object' then
            raise exception 'record must be an object';
        end if;
        if not (v_record ?& array['schema_version', 'journal_id', 'checkpoint', 'previous_record_digest', 'key_id', 'signature']) then
            raise exception 'record is missing required fields';
        end if;
        if (v_record - array[
            'schema_version', 'journal_id', 'checkpoint',
            'previous_record_digest', 'key_id', 'signature'
        ]) <> '{}'::jsonb then
            raise exception 'record contains unknown fields';
        end if;
        if pg_catalog.jsonb_typeof(v_record->'schema_version') <> 'number'
           or (v_record->>'schema_version')::integer <> 1 then
            raise exception 'unsupported record schema';
        end if;
        if v_record->>'journal_id' is distinct from p_journal_id then
            raise exception 'journal mismatch';
        end if;

        v_checkpoint := v_record->'checkpoint';
        if pg_catalog.jsonb_typeof(v_checkpoint) <> 'object'
           or not (v_checkpoint ?& array['schema_version', 'sequence', 'head_hash'])
           or (v_checkpoint - array['schema_version', 'sequence', 'head_hash']) <> '{}'::jsonb
           or pg_catalog.jsonb_typeof(v_checkpoint->'schema_version') <> 'number'
           or (v_checkpoint->>'schema_version')::integer <> 1
           or pg_catalog.jsonb_typeof(v_checkpoint->'sequence') <> 'number'
           or (v_checkpoint->>'sequence')::numeric < 0
           or (v_checkpoint->>'sequence')::numeric <> pg_catalog.trunc((v_checkpoint->>'sequence')::numeric)
 then
            raise exception 'invalid checkpoint envelope';
        end if;
        v_sequence := (v_checkpoint->>'sequence')::bigint;
        v_head_hash := v_checkpoint->>'head_hash';
        v_previous_digest := v_record->>'previous_record_digest';
        v_key_id := v_record->>'key_id';
        v_signature := v_record->>'signature';
    exception when others then
        raise exception 'Malformed audit anchor record' using errcode = '22023';
    end;

    if v_sequence < 0
       or v_head_hash is null or pg_catalog.length(v_head_hash) <> 64 or v_head_hash ~ '[^0-9a-f]'
       or (v_previous_digest is not null and (pg_catalog.length(v_previous_digest) <> 64 or v_previous_digest ~ '[^0-9a-f]'))
       or v_previous_digest is distinct from p_expected_digest
       or v_key_id is null or pg_catalog.length(v_key_id) not between 1 and 120 or v_key_id ~ '[^A-Za-z0-9_.:-]'

       or v_signature is null or pg_catalog.length(v_signature) = 0
       or pg_catalog.length(v_signature) > 2048 then
        raise exception 'Audit anchor record fields do not match pointer' using errcode = '22023';
    end if;

    -- Genesis insert; ON CONFLICT handles two concurrent first publishers.
    if p_expected_digest is null then
        insert into public.papi_audit_anchor_heads(
            journal_id, latest_record_digest, sequence, head_hash
        ) values (p_journal_id, p_new_digest, v_sequence, v_head_hash)
        on conflict (journal_id) do nothing;
        if found then
            return true;
        end if;
    end if;

    select * into v_current
      from public.papi_audit_anchor_heads
     where journal_id = p_journal_id
     for update;

    if not found then
        return false;
    end if;
    if v_current.latest_record_digest = p_new_digest then
        return v_current.sequence = v_sequence and v_current.head_hash = v_head_hash;
    end if;
    if v_current.latest_record_digest is distinct from p_expected_digest then
        return false;
    end if;
    if v_sequence <= v_current.sequence then
        raise exception 'Audit anchor sequence must increase' using errcode = '22023';
    end if;

    update public.papi_audit_anchor_heads
       set latest_record_digest = p_new_digest,
           sequence = v_sequence,
           head_hash = v_head_hash,
           updated_at = pg_catalog.now()
     where journal_id = p_journal_id;
    return true;
end;
$papi$;

revoke all on function public.papi_reject_audit_anchor_record_mutation() from public, anon, authenticated;
revoke all on function public.papi_advance_audit_anchor(text, text, text) from public, anon, authenticated;
grant execute on function public.papi_advance_audit_anchor(text, text, text) to service_role;
