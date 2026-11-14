-- Crash/retry and idempotency contracts on disposable PostgreSQL.
do $$
declare
  v_claim jsonb;
  v_status text;
  v_job_count integer;
begin
  insert into public.papi_tasks(id, task)
  values ('CI-IDEMPOTENCY-TASK', '{"id":"CI-IDEMPOTENCY-TASK","owner_agent":"ci-agent"}'::jsonb)
  on conflict (id) do nothing;

  insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, max_attempts)
  values ('CI-IDEMPOTENCY-JOB-1', 'CI-IDEMPOTENCY-TASK', 'test.noop',
          '{"operation":"record_once"}'::jsonb, 'ci-idempotency-business-op-01', 2)
  on conflict (id) do nothing;

  -- A retrying producer with the same idempotency key cannot create a second job.
  begin
    insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, max_attempts)
    values ('CI-IDEMPOTENCY-JOB-DUP', 'CI-IDEMPOTENCY-TASK', 'test.noop',
            '{"operation":"record_once"}'::jsonb, 'ci-idempotency-business-op-01', 2);
    raise exception 'Duplicate idempotency key was accepted';
  exception when unique_violation then
    null;
  end;

  select count(*) into v_job_count from public.papi_jobs
   where idempotency_key = 'ci-idempotency-business-op-01';
  if v_job_count <> 1 then
    raise exception 'Idempotency key produced % jobs instead of one', v_job_count;
  end if;

  -- Simulate a worker crash after claim: no completion is recorded, lease expiry
  -- permits a bounded retry, and the attempt ceiling makes the job terminal.
  v_claim := public.papi_claim_job('ci-idem-worker-a', gen_random_uuid(), 60);
  if v_claim is null or v_claim->>'id' <> 'CI-IDEMPOTENCY-JOB-1'
     or (v_claim->>'attempts')::integer <> 1 then
    raise exception 'Initial claim after simulated crash was not correct';
  end if;

  update public.papi_jobs set lease_until = now() - interval '1 second'
   where id = 'CI-IDEMPOTENCY-JOB-1' and status = 'running';
  v_claim := public.papi_claim_job('ci-idem-worker-b', gen_random_uuid(), 60);
  if v_claim is null or (v_claim->>'attempts')::integer <> 2 then
    raise exception 'Expired job was not reclaimed as attempt two';
  end if;

  v_status := public.papi_fail_job(
    'CI-IDEMPOTENCY-JOB-1', 'ci-idem-worker-b',
    (v_claim->>'lease_token')::uuid, 'ci_crash_retry_test'
  );
  if v_status <> 'failed' then
    raise exception 'Attempt ceiling did not make job terminal: %', v_status;
  end if;

  if exists (select 1 from public.papi_jobs
              where id = 'CI-IDEMPOTENCY-JOB-1' and status <> 'failed') then
    raise exception 'Terminal job status was not persisted';
  end if;

  if public.papi_claim_job('ci-idem-worker-c', gen_random_uuid(), 60) is not null then
    raise exception 'Terminal job was claimed beyond max_attempts';
  end if;
end;
$$;
