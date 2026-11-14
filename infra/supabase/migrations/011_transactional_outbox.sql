-- Mission 27: transactional outbox with stable idempotency keys and leased delivery.
-- The queue records intent only. It never calls an external provider.

create table if not exists public.papi_outbox (
    id uuid primary key default gen_random_uuid(),
    idempotency_key text not null unique
        check (idempotency_key ~ '^[A-Za-z0-9:_./-]{8,180}$'),
    event_type text not null
        check (event_type ~ '^[a-z][a-z0-9_.-]{1,99}$'),
    aggregate_id text not null check (length(aggregate_id) between 1 and 160),
    payload jsonb not null check (
        jsonb_typeof(payload) = 'object'
        and octet_length(payload::text) <= 16384
    ),
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'retry', 'delivered', 'dead_letter', 'cancelled')),
    attempts integer not null default 0 check (attempts >= 0),
    max_attempts integer not null default 5 check (max_attempts between 1 and 10),
    available_at timestamptz not null default now(),
    lease_owner text,
    lease_token uuid,
    lease_until timestamptz,
    last_error_code text check (last_error_code is null or last_error_code ~ '^[a-z0-9_]{1,80}$'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (
        (status = 'processing') =
        (lease_owner is not null and lease_token is not null and lease_until is not null)
    ),
    check (
        status not in ('delivered', 'dead_letter', 'cancelled')
        or (lease_owner is null and lease_token is null and lease_until is null)
    )
);

create index if not exists papi_outbox_ready_idx
    on public.papi_outbox(status, available_at, created_at)
    where status in ('pending', 'retry');
create index if not exists papi_outbox_expired_lease_idx
    on public.papi_outbox(lease_until, created_at)
    where status = 'processing';

create table if not exists public.papi_outbox_attempts (
    attempt_id uuid primary key default gen_random_uuid(),
    outbox_id uuid not null references public.papi_outbox(id) on delete restrict,
    attempt_no integer not null check (attempt_no >= 1),
    event_type text not null
        check (event_type in ('claimed', 'delivered', 'retry_scheduled', 'dead_lettered', 'lease_expired')),
    worker_id text not null check (length(worker_id) between 1 and 120),
    occurred_at timestamptz not null default now(),
    error_code text check (error_code is null or error_code ~ '^[a-z0-9_]{1,80}$'),
    unique (outbox_id, attempt_no, event_type)
);

create index if not exists papi_outbox_attempts_history_idx
    on public.papi_outbox_attempts(outbox_id, occurred_at);

alter table public.papi_outbox enable row level security;
alter table public.papi_outbox_attempts enable row level security;
revoke all on public.papi_outbox from public, anon, authenticated;
revoke all on public.papi_outbox_attempts from public, anon, authenticated;
grant select, insert, update on public.papi_outbox to service_role;
grant select, insert on public.papi_outbox_attempts to service_role;

-- Repeating the same key and identical intent returns the original ID.
-- Reusing a key for different intent is a hard conflict.
create or replace function public.papi_enqueue_outbox(
    p_idempotency_key text,
    p_event_type text,
    p_aggregate_id text,
    p_payload jsonb,
    p_max_attempts integer default 5
) returns uuid
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_id uuid;
    v_existing public.papi_outbox%rowtype;
begin
    if p_idempotency_key is null or p_idempotency_key !~ '^[A-Za-z0-9:_./-]{8,180}$'
       or p_event_type is null or p_event_type !~ '^[a-z][a-z0-9_.-]{1,99}$'
       or p_aggregate_id is null or length(trim(p_aggregate_id)) not between 1 and 160
       or p_payload is null or jsonb_typeof(p_payload) <> 'object'
       or octet_length(p_payload::text) > 16384
       or p_max_attempts is null or p_max_attempts not between 1 and 10 then
        raise exception 'Invalid outbox enqueue request' using errcode = '22023';
    end if;

    insert into public.papi_outbox(
        idempotency_key, event_type, aggregate_id, payload, max_attempts
    ) values (
        p_idempotency_key, p_event_type, p_aggregate_id, p_payload, p_max_attempts
    )
    on conflict (idempotency_key) do nothing
    returning id into v_id;

    if v_id is not null then
        return v_id;
    end if;

    select * into v_existing
      from public.papi_outbox
     where idempotency_key = p_idempotency_key;

    if not found then
        raise exception 'Outbox idempotency conflict; retry transaction'
            using errcode = '40001';
    end if;

    if v_existing.event_type is distinct from p_event_type
       or v_existing.aggregate_id is distinct from p_aggregate_id
       or v_existing.payload is distinct from p_payload
       or v_existing.max_attempts is distinct from p_max_attempts then
        raise exception 'Idempotency key already belongs to different intent'
            using errcode = '23505';
    end if;

    return v_existing.id;
end;
$$;

-- SKIP LOCKED lets multiple workers claim different events without blocking.
-- Expired leases are reclaimable with a fresh fencing token.
create or replace function public.papi_claim_outbox(
    p_worker_id text,
    p_lease_token uuid,
    p_lease_seconds integer default 120
) returns jsonb
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_item public.papi_outbox%rowtype;
    v_expired record;
begin
    if p_worker_id is null or length(trim(p_worker_id)) not between 1 and 120
       or p_lease_token is null or p_lease_seconds is null
       or p_lease_seconds not between 15 and 900 then
        raise exception 'Invalid outbox lease request' using errcode = '22023';
    end if;

    -- Terminalize exhausted leases before looking for claimable work.
    for v_expired in
        update public.papi_outbox
           set status = 'dead_letter',
               last_error_code = 'lease_expired_max_attempts',
               lease_owner = null, lease_token = null, lease_until = null,
               updated_at = now()
         where status = 'processing'
           and lease_until <= now()
           and attempts >= max_attempts
        returning id, attempts
    loop
        insert into public.papi_outbox_attempts(
            outbox_id, attempt_no, event_type, worker_id, error_code
        ) values (
            v_expired.id, v_expired.attempts, 'lease_expired',
            p_worker_id, 'lease_expired_max_attempts'
        );
        insert into public.papi_outbox_attempts(
            outbox_id, attempt_no, event_type, worker_id, error_code
        ) values (
            v_expired.id, v_expired.attempts, 'dead_lettered',
            p_worker_id, 'lease_expired_max_attempts'
        );
    end loop;

    select * into v_item
      from public.papi_outbox
     where attempts < max_attempts
       and (
          (status in ('pending', 'retry') and available_at <= now())
          or (status = 'processing' and lease_until <= now())
       )
     order by available_at, created_at
     for update skip locked
     limit 1;

    if not found then
        return null;
    end if;

    update public.papi_outbox
       set status = 'processing',
           attempts = attempts + 1,
           lease_owner = p_worker_id,
           lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_item.id
     returning * into v_item;

    insert into public.papi_outbox_attempts(
        outbox_id, attempt_no, event_type, worker_id
    ) values (v_item.id, v_item.attempts, 'claimed', p_worker_id);

    return jsonb_build_object(
        'id', v_item.id,
        'idempotency_key', v_item.idempotency_key,
        'event_type', v_item.event_type,
        'aggregate_id', v_item.aggregate_id,
        'payload', v_item.payload,
        'attempts', v_item.attempts,
        'max_attempts', v_item.max_attempts,
        'lease_token', v_item.lease_token,
        'lease_until', v_item.lease_until
    );
end;
$$;

-- Acknowledgement is fenced by both worker identity and lease token.
-- Failure schedules bounded exponential retry; no provider call is made here.
create or replace function public.papi_finish_outbox(
    p_outbox_id uuid,
    p_worker_id text,
    p_lease_token uuid,
    p_success boolean,
    p_error_code text default null
) returns text
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_item public.papi_outbox%rowtype;
    v_status text;
    v_event text;
begin
    if p_outbox_id is null or p_worker_id is null
       or length(trim(p_worker_id)) not between 1 and 120
       or p_lease_token is null or p_success is null
       or (p_success and p_error_code is not null)
       or (not p_success and (
            p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}$'
       )) then
        raise exception 'Invalid outbox completion request' using errcode = '22023';
    end if;

    select * into v_item
      from public.papi_outbox
     where id = p_outbox_id
       and status = 'processing'
       and lease_owner = p_worker_id
       and lease_token = p_lease_token
       and lease_until > now()
     for update;

    if not found then
        return 'stale_or_not_owned';
    end if;

    if p_success then
        v_status := 'delivered';
        v_event := 'delivered';
    elsif v_item.attempts >= v_item.max_attempts then
        v_status := 'dead_letter';
        v_event := 'dead_lettered';
    else
        v_status := 'retry';
        v_event := 'retry_scheduled';
    end if;

    update public.papi_outbox
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => least(
               3600, 15 * power(2, attempts - 1)::integer
             ))
             else available_at end,
           last_error_code = p_error_code,
           lease_owner = null, lease_token = null, lease_until = null,
           updated_at = now()
     where id = p_outbox_id;

    insert into public.papi_outbox_attempts(
        outbox_id, attempt_no, event_type, worker_id, error_code
    ) values (
        p_outbox_id, v_item.attempts, v_event, p_worker_id, p_error_code
    );

    return v_status;
end;
$$;

create or replace function public.papi_outbox_health()
returns jsonb
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
    select jsonb_build_object(
        'pending', count(*) filter (where status = 'pending'),
        'processing', count(*) filter (where status = 'processing'),
        'retry', count(*) filter (where status = 'retry'),
        'delivered', count(*) filter (where status = 'delivered'),
        'dead_letter', count(*) filter (where status = 'dead_letter'),
        'cancelled', count(*) filter (where status = 'cancelled'),
        'expired_leases', count(*) filter (
            where status = 'processing' and lease_until <= now()
        ),
        'ready_waiting', count(*) filter (
            where status in ('pending', 'retry') and available_at <= now()
        )
    )
    from public.papi_outbox;
$$;

revoke all on function public.papi_enqueue_outbox(text, text, text, jsonb, integer)
    from public, anon, authenticated;
revoke all on function public.papi_claim_outbox(text, uuid, integer)
    from public, anon, authenticated;
revoke all on function public.papi_finish_outbox(uuid, text, uuid, boolean, text)
    from public, anon, authenticated;
revoke all on function public.papi_outbox_health()
    from public, anon, authenticated;
grant execute on function public.papi_enqueue_outbox(text, text, text, jsonb, integer)
    to service_role;
grant execute on function public.papi_claim_outbox(text, uuid, integer)
    to service_role;
grant execute on function public.papi_finish_outbox(uuid, text, uuid, boolean, text)
    to service_role;
grant execute on function public.papi_outbox_health()
    to service_role;
