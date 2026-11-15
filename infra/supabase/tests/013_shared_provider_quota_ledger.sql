-- Mission 104: manual SQL contract tests. Run after schema.sql and migration 013.
-- Uses a transaction and rolls back all test data.
begin;

do $$
declare
    v record;
    v_again record;
    v_committed boolean;
    v_failed boolean := false;
begin
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

    begin
        perform * from public.papi_reserve_provider_quota(
            'test:quota:reserve:002', 'cloudflare', 'test-account', 'test-model',
            'TEST-WORKER-02', 50, 100, date '2099-01-01'
        );
    exception when others then
        v_failed := true;
    end;
    if not v_failed then raise exception 'quota overdraw was not rejected'; end if;

    v_committed := public.papi_commit_provider_quota(v.reservation_id, 55);
    if not v_committed then raise exception 'commit contract failed'; end if;

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
    exception when others then
        v_failed := true;
    end;
    if not v_failed then raise exception 'uncertain reservation was incorrectly released'; end if;

    if not exists (
        select 1 from public.papi_provider_daily_quotas
         where provider = 'cloudflare' and account_ref = 'test-account'
           and model = 'test-model' and quota_day = date '2099-01-01'
           and consumed_units = 55 and reserved_units = 20
    ) then raise exception 'quota bucket accounting mismatch'; end if;
end;
$$;

rollback;
