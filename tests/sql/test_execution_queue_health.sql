-- Queue health must expose aggregate counts only and must not leak job data.
do $$
declare
  v_before jsonb;
  v_after jsonb;
begin
  v_before := public.papi_execution_queue_health();

  insert into public.papi_tasks(id, task)
  values
    ('CI-QUEUE-HEALTH-001', '{"id":"CI-QUEUE-HEALTH-001"}'::jsonb),
    ('CI-QUEUE-HEALTH-002', '{"id":"CI-QUEUE-HEALTH-002"}'::jsonb),
    ('CI-QUEUE-HEALTH-003', '{"id":"CI-QUEUE-HEALTH-003"}'::jsonb),
    ('CI-QUEUE-HEALTH-004', '{"id":"CI-QUEUE-HEALTH-004"}'::jsonb);

  insert into public.papi_jobs(
    id, task_id, handler, payload, idempotency_key, status,
    attempts, max_attempts, available_at, lease_owner, lease_token, lease_until,
    last_error_code, created_at
  ) values
    ('CI-QUEUE-HEALTH-001', 'CI-QUEUE-HEALTH-001', 'test.read', '{"secret":"must-not-leak"}',
     'ci-queue-health-001', 'queued', 0, 5, now(), null, null, null, null, now() - interval '90 seconds'),
    ('CI-QUEUE-HEALTH-002', 'CI-QUEUE-HEALTH-002', 'test.read', '{}',
     'ci-queue-health-002', 'retry', 1, 5, now(), null, null, null, 'temporary_error', now() - interval '60 seconds'),
    ('CI-QUEUE-HEALTH-003', 'CI-QUEUE-HEALTH-003', 'test.read', '{}',
     'ci-queue-health-003', 'running', 1, 5, now(), 'ci-worker',
     '00000000-0000-4000-8000-000000000003', now() - interval '30 seconds', null, now()),
    ('CI-QUEUE-HEALTH-004', 'CI-QUEUE-HEALTH-004', 'test.read', '{}',
     'ci-queue-health-004', 'failed', 5, 5, now(), null, null, null, 'terminal_error', now());

  v_after := public.papi_execution_queue_health();

  if (v_after->>'queued')::integer - (v_before->>'queued')::integer <> 1
     or (v_after->>'retry')::integer - (v_before->>'retry')::integer <> 1
     or (v_after->>'running')::integer - (v_before->>'running')::integer <> 1
     or (v_after->>'failed')::integer - (v_before->>'failed')::integer <> 1
     or (v_after->>'expired_leases')::integer - (v_before->>'expired_leases')::integer <> 1
     or (v_after->>'ready_waiting')::integer - (v_before->>'ready_waiting')::integer <> 2 then
    raise exception 'Queue health aggregate counts are inconsistent: %', v_after;
  end if;

  if v_after ? 'payload' or v_after ? 'result' or v_after ? 'job_id'
     or v_after ? 'lease_token' or v_after::text like '%must-not-leak%' then
    raise exception 'Queue health response leaked job-level data';
  end if;

  if not has_function_privilege('service_role', 'public.papi_execution_queue_health()', 'execute')
     or has_function_privilege('anon', 'public.papi_execution_queue_health()', 'execute')
     or has_function_privilege('authenticated', 'public.papi_execution_queue_health()', 'execute') then
    raise exception 'Queue health function privileges are too broad or incomplete';
  end if;
end;
$$;
