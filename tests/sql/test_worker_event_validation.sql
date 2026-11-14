-- Invalid event envelope and atomicity contracts for worker synchronization.
do $$
declare
  v_count integer;
begin
  -- Unsupported domain is rejected before any persistence.
  begin
    perform public.papi_sync_worker_record(
      'unknown_domain', 'CI-EVENT-INVALID-001', 0,
      'WEVT-CI-INVALID-000000000000000000000000000001', repeat('d',64),
      'ci-invalid-domain', 'event_created', 'ci-agent',
      '{"ok":true}'::jsonb, now()
    );
    raise exception 'Unsupported worker event domain was accepted';
  exception when sqlstate '22023' then null;
  end;

  -- Idempotency digest must be exactly 64 lowercase hexadecimal characters.
  begin
    perform public.papi_sync_worker_record(
      'human_handoff', 'CI-EVENT-INVALID-002', 0,
      'WEVT-CI-INVALID-000000000000000000000000000002', 'not-a-sha256-digest',
      'ci-invalid-digest', 'event_created', 'ci-agent',
      '{"ok":true}'::jsonb, now()
    );
    raise exception 'Malformed event idempotency digest was accepted';
  exception when sqlstate '22023' then null;
  end;

  -- Event envelope requires a JSON object, not scalar or array payload.
  begin
    perform public.papi_sync_worker_record(
      'human_handoff', 'CI-EVENT-INVALID-003', 0,
      'WEVT-CI-INVALID-000000000000000000000000000003', repeat('e',64),
      'ci-invalid-payload', 'event_created', 'ci-agent',
      '["not","an","object"]'::jsonb, now()
    );
    raise exception 'Non-object event payload was accepted';
  exception when sqlstate '22023' then null;
  end;

  -- Blank event identity fields are rejected.
  begin
    perform public.papi_sync_worker_record(
      'human_handoff', 'CI-EVENT-INVALID-004', 0,
      'WEVT-CI-INVALID-000000000000000000000000000004', repeat('f',64),
      'ci-invalid-actor', 'event_created', '   ',
      '{"ok":true}'::jsonb, now()
    );
    raise exception 'Blank event actor was accepted';
  exception when sqlstate '22023' then null;
  end;

  select count(*) into v_count
    from public.papi_worker_records
   where record_id like 'CI-EVENT-INVALID-%';
  if v_count <> 0 then
    raise exception 'Invalid event envelopes left % worker records behind', v_count;
  end if;

  select count(*) into v_count
    from public.papi_worker_event_receipts
   where record_id like 'CI-EVENT-INVALID-%';
  if v_count <> 0 then
    raise exception 'Invalid event envelopes left % receipts behind', v_count;
  end if;
end;
$$;
