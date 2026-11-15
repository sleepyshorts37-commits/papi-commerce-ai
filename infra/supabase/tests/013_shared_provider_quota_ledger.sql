-- Mission 104/108: manual SQL contract and security tests.
-- Run after schema.sql and migration 013. All test data is rolled back.
begin;

do $$
declare
    v record;
    v_again record;
    v_committed boolean;
    v_failed boolean := false;
    v_released uuid;
begin
    -- Backend-only access model: RLS enabled, no public client table/RPC access.
    if not (select relrowsecurity from pg_class
             where oid = 'public.papi_provider_daily_quotas'::regclass) then
        raise exception 'RLS missing on daily quota table';
    end if;
    if not (select relrowsecurity from pg_class
             where oid = 'public.papi_provider_quota_reservations'::regclass) then
        raise exception 'RLS missing on reservations table';
    end if;
    if has_table_privilege('anon', 'public.papi_provider_daily_quotas', 'SELECT')
       or has_table_privilege('authenticated', 'public.papi_provider_daily_quotas', 'SELECT')
       or has_table_privilege('anon', 'public.papi_provider_quota_reservations', 'SELECT')
       or has_table_privilege('authenticated', 'public.papi_provider_quota_reservations', 'SELECT') then
        raise exception 'public client role unexpectedly has quota table access';
    end if;
    if has_function_privilege('anon',
       'public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date)', 'EXECUTE')
       or has_function_privilege('authenticated',
       'public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date)', 'EXECUTE') then
        raise exception 'public client role unexpectedly can execute quota RPC';
    end if;
    if not has_table_privilege('service_role', 'public.papi_provider_daily_quotas', 'SELECT')
       or not has_table_privilege('service_role', 'public.papi_provider_quota_reservations', 'SELECT')
       or not has_function_privilege('service_role',
       'public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date)', 'EXECUTE') then
        raise exception 'service_role quota privileges missing';
    end if;

    -- Reserve and replay same intent: one reservation only.
    select * into v from public.papi_reserve_provider_quota(
        'test:quota:reserve:001', 'cloudflare', 'test-account', 'test-model',
        'TEST-WORKER-01', 60, 100, date '2099-01-01'
    );
    if v.reservation_status <> 'reserved' or v.reserved_units <> 60 then
        raise exception 'reserve contract failed';
    end if;
    select * into v_again from public.papi_reserve_provider_quota(
        'test:quota:reserve:001', 'cloudflare', 'test-account', 'test-model',
        'TEST-WORKER-01', 60, 100, date '2099-01-01'
    );
    if v.reservation_id <> v_again.reservation_id or v_again.reserved_units <> 60 then
        raise exception 'idempotency contract failed';
    end if;
    if v_again.reservation_status <> 'reused_reserved' then
        raise exception 'replayed reserved key was not marked as reused_reserved';
    end if;

    -- Different intent on the same key must be rejected.
    v_failed := false;
    begin
        perform * from public.papi_reserve_provider_quota(
            'test:quota:reserve:001', 'cloudflare', 'test-account', 'test-model',
            'TEST-WORKER-01', 50, 100, date '2099-01-01'
        );
    exception when others then v_failed := true;
    end;
    if not v_failed then raise exception 'idempotency intent mismatch was accepted'; end if;

    -- Overdraw is rejected transactionally.
    v_failed := false;
    begin
        perform * from public.papi_reserve_provider_quota(
            'test:quota:reserve:002', 'cloudflare', 'test-account', 'test-model',
            'TEST-WORKER-02', 50, 100, date '2099-01-01'
        );
    exception when others then v_failed := true;
    end;
    if not v_failed then raise exception 'quota overdraw was not rejected'; end if;

    -- Commit is idempotent for identical usage and immutable for changed usage.
    v_committed := public.papi_commit_provider_quota(v.reservation_id, 55);
    if not v_committed then raise exception 'commit contract failed'; end if;
    if not public.papi_commit_provider_quota(v.reservation_id, 55) then
        raise exception 'repeat commit contract failed';
    end if;
    v_failed := false;
    begin
        perform public.papi_commit_provider_quota(v.reservation_id, 54);
    exception when others then v_failed := true;
    end;
    if not v_failed then raise exception 'committed usage was mutable'; end if;

    -- Uncertain holds capacity and cannot be released; it can be reconciled by commit.
    select * into v from public.papi_reserve_provider_quota(
        'test:quota:reserve:003', 'cloudflare', 'test-account', 'test-model',
        'TEST-WORKER-03', 20, 100, date '2099-01-01'
    );
    if not public.papi_mark_provider_quota_uncertain(v.reservation_id) then
        raise exception 'uncertain transition failed';
    end if;
    v_failed := false;
    begin
        perform public.papi_release_provider_quota(v.reservation_id);
    exception when others then v_failed := true;
    end;
    if not v_failed then raise exception 'uncertain reservation was incorrectly released'; end if;
    if not public.papi_commit_provider_quota(v.reservation_id, 15) then
        raise exception 'uncertain reconciliation commit failed';
    end if;

    -- A definitely unsubmitted reservation can be released exactly once/idempotently.
    select * into v from public.papi_reserve_provider_quota(
        'test:quota:reserve:004', 'cloudflare', 'test-account', 'test-model',
        'TEST-WORKER-04', 10, 100, date '2099-01-01'
    );
    v_released := v.reservation_id;
    if not public.papi_release_provider_quota(v_released)
       or not public.papi_release_provider_quota(v_released) then
        raise exception 'release/idempotent release contract failed';
    end if;
    select * into v_again from public.papi_reserve_provider_quota(
        'test:quota:reserve:004', 'cloudflare', 'test-account', 'test-model',
        'TEST-WORKER-04', 10, 100, date '2099-01-01'
    );
    if v_again.reservation_status <> 'released' then
        raise exception 'released idempotency state was not preserved';
    end if;
    v_failed := false;
    begin
        perform public.papi_commit_provider_quota(v_released, 10);
    exception when others then v_failed := true;
    end;
    if not v_failed then raise exception 'released reservation was committed'; end if;

    if not exists (
        select 1 from public.papi_provider_daily_quotas
         where provider = 'cloudflare' and account_ref = 'test-account'
           and model = 'test-model' and quota_day = date '2099-01-01'
           and consumed_units = 70 and reserved_units = 0
    ) then raise exception 'quota bucket accounting mismatch'; end if;
end;
$$;

rollback;
