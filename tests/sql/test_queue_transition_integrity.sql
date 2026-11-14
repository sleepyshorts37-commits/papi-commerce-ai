-- Verify queue transition consistency and generic error observability without exposing error codes.
begin;
do $$
declare
  v_claim jsonb;
  v_summary jsonb;
  v_completed boolean;
begin
  insert into public.papi_tasks(id, task)
  values ('CI-QUEUE-TRANSITION-TASK', '{"id":"CI-QUEUE-TRANSITION-TASK"}'::jsonb)
  on conflict (id) do nothing;

  insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, max_attempts)
  values ('CI-QUEUE-TRANSITION-JOB', 'CI-QUEUE-TRANSITION-TASK', 'test.noop', '{}',
          'ci-queue-transition-key', 3)
  on conflict (id) do nothing;

  -- The database rejects a running row without a complete lease tuple.
  begin
    update public.papi_jobs set status = 'running'
     where id = 'CI-QUEUE-TRANSITION-JOB';
    raise exception 'Running state without lease was accepted';
  exception when check_violation then
    null;
  end;

  v_claim := public.papi_claim_job('ci-transition-worker-a', gen_random_uuid(), 60);
  if v_claim is null or v_claim->>'id' <> 'CI-QUEUE-TRANSITION-JOB' then
    raise exception 'Queue job could not be claimed for transition test';
  end if;

  if public.papi_fail_job(
      'CI-QUEUE-TRANSITION-JOB', 'ci-transition-worker-a',
      (v_claim->>'lease_token')::uuid, 'ci_transient_failure'
  ) <> 'retry' then
    raise exception 'Expected failed attempt to transition to retry';
  end if;

  update public.papi_jobs set available_at = now() - interval '1 second'
   where id = 'CI-QUEUE-TRANSITION-JOB';
  v_summary := public.papi_execution_queue_error_summary();

  if (v_summary->>'retry_with_error')::integer < 1
     or (v_summary->>'retry_without_error')::integer < 0 then
    raise exception 'Generic retry error summary did not reflect the retry state';
  end if;
  if v_summary::text like '%ci_transient_failure%' then
    raise exception 'Generic error summary leaked a raw error code';
  end if;

  v_claim := public.papi_claim_job('ci-transition-worker-b', gen_random_uuid(), 60);
  if v_claim is null or v_claim->>'id' <> 'CI-QUEUE-TRANSITION-JOB' then
    raise exception 'Retry job was not claimable for successful completion';
  end if;

  v_completed := public.papi_complete_job(
    'CI-QUEUE-TRANSITION-JOB', 'ci-transition-worker-b',
    (v_claim->>'lease_token')::uuid, '{"ok":true}'::jsonb
  );
  if not v_completed then
    raise exception 'Current lease owner could not complete retry job';
  end if;

  if exists (select 1 from public.papi_jobs
              where id = 'CI-QUEUE-TRANSITION-JOB'
                and (status <> 'done' or last_error_code is not null
                     or lease_owner is not null or lease_token is not null
                     or lease_until is not null)) then
    raise exception 'Successful completion did not clear error and lease metadata';
  end if;

  v_summary := public.papi_execution_queue_error_summary();
  if (v_summary->>'done_with_error')::integer <> 0 then
    raise exception 'Completed jobs retained an error marker';
  end if;

  if not has_function_privilege('service_role', 'public.papi_execution_queue_error_summary()', 'execute')
     or has_function_privilege('anon', 'public.papi_execution_queue_error_summary()', 'execute')
     or has_function_privilege('authenticated', 'public.papi_execution_queue_error_summary()', 'execute') then
    raise exception 'Error summary function privileges are too broad or incomplete';
  end if;
end;
$$;
rollback;
