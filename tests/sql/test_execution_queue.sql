-- Real PostgreSQL contract tests for queue claims, lease ownership and recovery.
-- Run after infra/supabase/schema.sql with a disposable database.
do $$
declare
    v_claim_a jsonb;
    v_claim_b jsonb;
    v_reclaimed jsonb;
    v_job_id text;
    v_old_token uuid;
    v_new_token uuid;
    v_done boolean;
    v_retry text;
begin
    insert into public.papi_tasks(id, task)
    values
      ('CI-QUEUE-TASK-A', '{"id":"CI-QUEUE-TASK-A","owner_agent":"ci-agent"}'::jsonb),
      ('CI-QUEUE-TASK-B', '{"id":"CI-QUEUE-TASK-B","owner_agent":"ci-agent"}'::jsonb)
    on conflict (id) do nothing;

    insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, max_attempts)
    values
      ('CI-QUEUE-JOB-A', 'CI-QUEUE-TASK-A', 'test.noop', '{}'::jsonb, 'ci-queue-idem-a', 4),
      ('CI-QUEUE-JOB-B', 'CI-QUEUE-TASK-B', 'test.noop', '{}'::jsonb, 'ci-queue-idem-b', 4)
    on conflict (id) do nothing;

    v_claim_a := public.papi_claim_job('ci-worker-a', gen_random_uuid(), 60);
    v_claim_b := public.papi_claim_job('ci-worker-b', gen_random_uuid(), 60);

    if v_claim_a is null or v_claim_b is null
       or v_claim_a->>'id' = v_claim_b->>'id' then
        raise exception 'Two worker claims did not receive distinct jobs';
    end if;

    v_job_id := v_claim_a->>'id';
    v_old_token := (v_claim_a->>'lease_token')::uuid;

    v_done := public.papi_complete_job(v_job_id, 'different-worker', v_old_token, '{"ok":true}'::jsonb);
    if v_done then
        raise exception 'A different worker completed a job it did not own';
    end if;

    v_done := public.papi_complete_job(v_job_id, 'ci-worker-a', gen_random_uuid(), '{"ok":true}'::jsonb);
    if v_done then
        raise exception 'A stale/incorrect lease token completed a job';
    end if;

    v_done := public.papi_complete_job(v_job_id, 'ci-worker-a', v_old_token, '{"ok":true}'::jsonb);
    if not v_done then
        raise exception 'Current lease owner could not complete its job';
    end if;

    -- Exercise failure transition and bounded retry path on worker B's claim.
    v_job_id := v_claim_b->>'id';
    v_old_token := (v_claim_b->>'lease_token')::uuid;
    v_retry := public.papi_fail_job(v_job_id, 'ci-worker-b', v_old_token, 'ci_test_failure');
    if v_retry <> 'retry' then
        raise exception 'Expected retry state, received %', v_retry;
    end if;

    update public.papi_jobs set available_at = now() - interval '1 second'
     where id = v_job_id and status = 'retry';
    v_reclaimed := public.papi_claim_job('ci-worker-c', gen_random_uuid(), 60);
    if v_reclaimed is null or v_reclaimed->>'id' <> v_job_id
       or (v_reclaimed->>'attempts')::integer <> 2 then
        raise exception 'Retry job was not reclaimed with incremented attempt count';
    end if;

    -- Expire the active lease and prove that a new token fences the previous owner.
    v_old_token := (v_reclaimed->>'lease_token')::uuid;
    update public.papi_jobs set lease_until = now() - interval '1 second'
     where id = v_job_id and status = 'running';
    v_claim_a := public.papi_claim_job('ci-worker-d', gen_random_uuid(), 60);
    if v_claim_a is null or v_claim_a->>'id' <> v_job_id then
        raise exception 'Expired lease was not recovered';
    end if;
    v_new_token := (v_claim_a->>'lease_token')::uuid;
    if v_new_token = v_old_token then
        raise exception 'Recovered lease reused the old token';
    end if;
    v_done := public.papi_complete_job(v_job_id, 'ci-worker-c', v_old_token, '{"stale":true}'::jsonb);
    if v_done then
        raise exception 'Previous lease owner completed after lease recovery';
    end if;
    v_done := public.papi_complete_job(v_job_id, 'ci-worker-d', v_new_token, '{"recovered":true}'::jsonb);
    if not v_done then
        raise exception 'New lease owner could not complete recovered job';
    end if;

    if exists (
      select 1 from public.papi_jobs
       where id in ('CI-QUEUE-JOB-A', 'CI-QUEUE-JOB-B')
         and status <> 'done'
    ) then
      raise exception 'Queue lifecycle did not finish in done state';
    end if;
end;
$$;
