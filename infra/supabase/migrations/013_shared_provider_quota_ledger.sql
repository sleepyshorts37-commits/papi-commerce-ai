-- Mission 104: shared, transactional provider quota ledger.
-- All quota arithmetic is performed under a row lock in PostgreSQL.
-- Tables are backend-only; no anon/authenticated Data API access is granted.

create table if not exists public.papi_provider_daily_quotas (
    provider text not null check (provider ~ '^[a-z][a-z0-9_-]{1,39}$'),
    account_ref text not null check (length(trim(account_ref)) between 1 and 160),
    model text not null check (length(trim(model)) between 1 and 200),
    quota_day date not null,
    daily_limit bigint not null check (daily_limit > 0),
    reserved_units bigint not null default 0 check (reserved_units >= 0),
    consumed_units bigint not null default 0 check (consumed_units >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (provider, account_ref, model, quota_day),
    check (reserved_units + consumed_units <= daily_limit)
);

create table if not exists public.papi_provider_quota_reservations (
    reservation_id uuid primary key default gen_random_uuid(),
    idempotency_key text not null unique
        check (idempotency_key ~ '^[A-Za-z0-9:_./-]{8,180}$'),
    provider text not null,
    account_ref text not null,
    model text not null,
    quota_day date not null,
    worker_id text not null check (length(trim(worker_id)) between 1 and 120),
    estimated_units bigint not null check (estimated_units > 0),
    actual_units bigint check (actual_units is null or actual_units > 0),
    status text not null default 'reserved'
        check (status in ('reserved', 'committed', 'released', 'uncertain')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    committed_at timestamptz,
    released_at timestamptz,
    foreign key (provider, account_ref, model, quota_day)
        references public.papi_provider_daily_quotas(provider, account_ref, model, quota_day)
        on delete restrict,
    check (
        (status = 'committed' and actual_units is not null and committed_at is not null)
        or status <> 'committed'
    ),
    check (
        (status = 'released' and released_at is not null)
        or status <> 'released'
    )
);

create index if not exists papi_provider_quota_reservations_day_idx
    on public.papi_provider_quota_reservations(provider, account_ref, model, quota_day, status);

alter table public.papi_provider_daily_quotas enable row level security;
alter table public.papi_provider_quota_reservations enable row level security;
revoke all on public.papi_provider_daily_quotas from public, anon, authenticated;
revoke all on public.papi_provider_quota_reservations from public, anon, authenticated;
grant select, insert, update on public.papi_provider_daily_quotas to service_role;
grant select, insert, update on public.papi_provider_quota_reservations to service_role;

-- Serializes duplicate idempotency keys, then locks the quota bucket.
-- Returns the existing reservation only when the original intent matches.
create or replace function public.papi_reserve_provider_quota(
    p_idempotency_key text,
    p_provider text,
    p_account_ref text,
    p_model text,
    p_worker_id text,
    p_estimated_units bigint,
    p_daily_limit bigint,
    p_quota_day date default ((now() at time zone 'utc')::date)
) returns table (
    reservation_id uuid,
    reservation_status text,
    quota_day date,
    reserved_units bigint,
    consumed_units bigint,
    daily_limit bigint
)
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_existing public.papi_provider_quota_reservations%rowtype;
    v_bucket public.papi_provider_daily_quotas%rowtype;
    v_id uuid;
begin
    if p_idempotency_key is null or p_idempotency_key !~ '^[A-Za-z0-9:_./-]{8,180}$'
       or p_provider is null or p_provider !~ '^[a-z][a-z0-9_-]{1,39}$'
       or p_account_ref is null or length(trim(p_account_ref)) not between 1 and 160
       or p_model is null or length(trim(p_model)) not between 1 and 200
       or p_worker_id is null or length(trim(p_worker_id)) not between 1 and 120
       or p_estimated_units is null or p_estimated_units <= 0
       or p_daily_limit is null or p_daily_limit <= 0
       or p_quota_day is null then
        raise exception 'Invalid provider quota reservation' using errcode = '22023';
    end if;

    -- A transaction-scoped advisory lock prevents races on the global idempotency key.
    perform pg_advisory_xact_lock(hashtextextended('papi-quota:' || p_idempotency_key, 0));

    select * into v_existing
      from public.papi_provider_quota_reservations
     where idempotency_key = p_idempotency_key;

    if found then
        if v_existing.provider <> p_provider
           or v_existing.account_ref <> p_account_ref
           or v_existing.model <> p_model
           or v_existing.worker_id <> p_worker_id
           or v_existing.quota_day <> p_quota_day
           or v_existing.estimated_units <> p_estimated_units then
            raise exception 'Idempotency key reused with different quota intent' using errcode = '23505';
        end if;
        select * into v_bucket from public.papi_provider_daily_quotas
         where provider = v_existing.provider and account_ref = v_existing.account_ref
           and model = v_existing.model and quota_day = v_existing.quota_day;
        return query select v_existing.reservation_id, v_existing.status,
            v_bucket.quota_day, v_bucket.reserved_units, v_bucket.consumed_units, v_bucket.daily_limit;
        return;
    end if;

    insert into public.papi_provider_daily_quotas(provider, account_ref, model, quota_day, daily_limit)
    values (p_provider, p_account_ref, p_model, p_quota_day, p_daily_limit)
    on conflict (provider, account_ref, model, quota_day) do nothing;

    select * into v_bucket
      from public.papi_provider_daily_quotas
     where provider = p_provider and account_ref = p_account_ref
       and model = p_model and quota_day = p_quota_day
     for update;

    if v_bucket.daily_limit <> p_daily_limit then
        raise exception 'Daily quota limit mismatch for existing bucket' using errcode = '22023';
    end if;
    if v_bucket.reserved_units + v_bucket.consumed_units + p_estimated_units > v_bucket.daily_limit then
        raise exception 'Provider daily quota exceeded' using errcode = 'P0001';
    end if;

    insert into public.papi_provider_quota_reservations(
        idempotency_key, provider, account_ref, model, quota_day,
        worker_id, estimated_units, status
    ) values (
        p_idempotency_key, p_provider, p_account_ref, p_model, p_quota_day,
        p_worker_id, p_estimated_units, 'reserved'
    ) returning public.papi_provider_quota_reservations.reservation_id into v_id;

    update public.papi_provider_daily_quotas
       set reserved_units = reserved_units + p_estimated_units, updated_at = now()
     where provider = p_provider and account_ref = p_account_ref
       and model = p_model and quota_day = p_quota_day
    returning * into v_bucket;

    return query select v_id, 'reserved'::text, v_bucket.quota_day,
        v_bucket.reserved_units, v_bucket.consumed_units, v_bucket.daily_limit;
end;
$$;

-- Commit converts reserved estimate into measured consumption.
-- If actual usage would breach the cap, the transaction fails and reservation remains held.
create or replace function public.papi_commit_provider_quota(
    p_reservation_id uuid,
    p_actual_units bigint
) returns boolean
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_res public.papi_provider_quota_reservations%rowtype;
    v_bucket public.papi_provider_daily_quotas%rowtype;
begin
    if p_reservation_id is null or p_actual_units is null or p_actual_units <= 0 then
        raise exception 'Invalid quota commit' using errcode = '22023';
    end if;
    select * into v_res from public.papi_provider_quota_reservations
     where reservation_id = p_reservation_id for update;
    if not found then raise exception 'Quota reservation not found' using errcode = 'P0002'; end if;
    if v_res.status = 'committed' then
        if v_res.actual_units <> p_actual_units then
            raise exception 'Committed usage cannot be changed' using errcode = '23505';
        end if;
        return true;
    end if;
    if v_res.status not in ('reserved', 'uncertain') then
        raise exception 'Quota reservation is already closed' using errcode = '55000';
    end if;

    select * into v_bucket from public.papi_provider_daily_quotas
     where provider = v_res.provider and account_ref = v_res.account_ref
       and model = v_res.model and quota_day = v_res.quota_day
     for update;
    if v_bucket.consumed_units + (v_bucket.reserved_units - v_res.estimated_units) + p_actual_units > v_bucket.daily_limit then
        raise exception 'Actual provider usage would exceed daily quota; reservation retained' using errcode = 'P0001';
    end if;

    update public.papi_provider_daily_quotas
       set reserved_units = reserved_units - v_res.estimated_units,
           consumed_units = consumed_units + p_actual_units, updated_at = now()
     where provider = v_res.provider and account_ref = v_res.account_ref
       and model = v_res.model and quota_day = v_res.quota_day;
    update public.papi_provider_quota_reservations
       set status = 'committed', actual_units = p_actual_units,
           committed_at = now(), updated_at = now()
     where reservation_id = p_reservation_id;
    return true;
end;
$$;

-- Uncertain provider outcomes retain their reservation and therefore block overspending.
create or replace function public.papi_mark_provider_quota_uncertain(p_reservation_id uuid)
returns boolean
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
begin
    update public.papi_provider_quota_reservations
       set status = 'uncertain', updated_at = now()
     where reservation_id = p_reservation_id and status = 'reserved';
    if found then return true; end if;
    if exists (select 1 from public.papi_provider_quota_reservations
               where reservation_id = p_reservation_id and status = 'uncertain') then
        return true;
    end if;
    raise exception 'Reservation not found or cannot become uncertain' using errcode = '55000';
end;
$$;

-- Only a definitely-not-submitted request may be released by the caller.
-- Uncertain reservations cannot be released through this function.
create or replace function public.papi_release_provider_quota(p_reservation_id uuid)
returns boolean
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_res public.papi_provider_quota_reservations%rowtype;
begin
    select * into v_res from public.papi_provider_quota_reservations
     where reservation_id = p_reservation_id for update;
    if not found then raise exception 'Quota reservation not found' using errcode = 'P0002'; end if;
    if v_res.status = 'released' then return true; end if;
    if v_res.status <> 'reserved' then
        raise exception 'Only a definitely unsubmitted reservation can be released' using errcode = '55000';
    end if;
    update public.papi_provider_daily_quotas
       set reserved_units = reserved_units - v_res.estimated_units, updated_at = now()
     where provider = v_res.provider and account_ref = v_res.account_ref
       and model = v_res.model and quota_day = v_res.quota_day;
    update public.papi_provider_quota_reservations
       set status = 'released', released_at = now(), updated_at = now()
     where reservation_id = p_reservation_id;
    return true;
end;
$$;

revoke all on function public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date) from public, anon, authenticated;
revoke all on function public.papi_commit_provider_quota(uuid,bigint) from public, anon, authenticated;
revoke all on function public.papi_mark_provider_quota_uncertain(uuid) from public, anon, authenticated;
revoke all on function public.papi_release_provider_quota(uuid) from public, anon, authenticated;
grant execute on function public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date) to service_role;
grant execute on function public.papi_commit_provider_quota(uuid,bigint) to service_role;
grant execute on function public.papi_mark_provider_quota_uncertain(uuid) to service_role;
grant execute on function public.papi_release_provider_quota(uuid) to service_role;
