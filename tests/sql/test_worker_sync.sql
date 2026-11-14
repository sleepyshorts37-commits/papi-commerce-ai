-- PostgreSQL integration checks for PAPI worker persistence.
-- Run after infra/supabase/schema.sql with anon/authenticated/service_role roles present.
do $$
declare
    v_first jsonb;
    v_replay jsonb;
    v_updated jsonb;
    v_version bigint;
    v_count integer;
begin
    v_first := public.papi_sync_worker_record(
        'human_handoff', 'CI-HANDOFF-001', 0,
        'WEVT-CI-00000000000000000000000000000001', repeat('a', 64),
        'ci-source-event-1', 'handoff_created', 'ci-agent',
        '{"status":"awaiting_user"}'::jsonb, '2026-11-14T08:00:00Z'::timestamptz
    );
    if (v_first->>'duplicate')::boolean is distinct from false
       or (v_first->>'record_version')::bigint <> 1 then
        raise exception 'Initial worker event was not persisted at version 1';
    end if;

    v_replay := public.papi_sync_worker_record(
        'human_handoff', 'CI-HANDOFF-001', 0,
        'WEVT-CI-00000000000000000000000000000001', repeat('a', 64),
        'ci-source-event-1', 'handoff_created', 'ci-agent',
        '{"status":"awaiting_user"}'::jsonb, '2026-11-14T08:00:00Z'::timestamptz
    );
    if (v_replay->>'duplicate')::boolean is distinct from true
       or (v_replay->>'record_version')::bigint <> 1 then
        raise exception 'Idempotent replay was not recognized';
    end if;

    begin
        perform public.papi_sync_worker_record(
            'human_handoff', 'CI-HANDOFF-001', 0,
            'WEVT-CI-00000000000000000000000000000001', repeat('a', 64),
            'ci-source-event-1', 'handoff_created', 'ci-agent',
            '{"status":"tampered"}'::jsonb, '2026-11-14T08:00:00Z'::timestamptz
        );
        raise exception 'Expected idempotency payload mismatch to fail';
    exception when sqlstate '22023' then
        null;
    end;

    v_updated := public.papi_sync_worker_record(
        'human_handoff', 'CI-HANDOFF-001', 1,
        'WEVT-CI-00000000000000000000000000000002', repeat('b', 64),
        'ci-source-event-2', 'handoff_status_updated', 'ci-agent',
        '{"status":"user_confirmed"}'::jsonb, '2026-11-14T08:05:00Z'::timestamptz
    );
    if (v_updated->>'duplicate')::boolean is distinct from false
       or (v_updated->>'record_version')::bigint <> 2 then
        raise exception 'Worker record update did not reach version 2';
    end if;

    begin
        perform public.papi_sync_worker_record(
            'human_handoff', 'CI-HANDOFF-001', 1,
            'WEVT-CI-00000000000000000000000000000003', repeat('c', 64),
            'ci-source-event-3', 'stale_update', 'ci-agent',
            '{"status":"stale"}'::jsonb, '2026-11-14T08:10:00Z'::timestamptz
        );
        raise exception 'Expected stale version to fail';
    exception when sqlstate '40001' then
        null;
    end;

    select version into v_version from public.papi_worker_records
     where domain = 'human_handoff' and record_id = 'CI-HANDOFF-001';
    if v_version <> 2 then
        raise exception 'Unexpected worker record version: %', v_version;
    end if;

    select count(*) into v_count from public.papi_worker_event_receipts
     where domain = 'human_handoff' and record_id = 'CI-HANDOFF-001';
    if v_count <> 2 then
        raise exception 'Expected exactly two accepted event receipts, got %', v_count;
    end if;

    select count(*) into v_count from public.papi_audit_events
     where entity_type = 'worker_human_handoff' and entity_id = 'CI-HANDOFF-001';
    if v_count <> 2 then
        raise exception 'Expected exactly two audit events, got %', v_count;
    end if;

    if has_table_privilege('anon', 'public.papi_worker_records', 'SELECT')
       or has_table_privilege('authenticated', 'public.papi_worker_records', 'SELECT') then
        raise exception 'Public API roles unexpectedly have access to worker records';
    end if;
    if not has_table_privilege('service_role', 'public.papi_worker_records', 'SELECT')
       or not has_table_privilege('service_role', 'public.papi_worker_event_receipts', 'INSERT') then
        raise exception 'service_role is missing required worker persistence privileges';
    end if;
end;
$$;
