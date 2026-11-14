-- Retention preview must be read-only and include only old terminal jobs as eligible.
begin;
do $$
declare
  v_before bigint;
  v_after bigint;
  v_preview jsonb;
  v_cutoff timestamptz := now() - interval '30 days';
begin
  insert into public.papi_tasks(id, task)
  values
    ('CI-RETENTION-TASK-1', '{"id":"CI-RETENTION-TASK-1"}'::jsonb),
    ('CI-RETENTION-TASK-2', '{"id":"CI-RETENTION-TASK-2"}'::jsonb),
    ('CI-RETENTION-TASK-3', '{"id":"CI-RETENTION-TASK-3"}'::jsonb),
    ('CI-RETENTION-TASK-4', '{"id":"CI-RETENTION-TASK-4"}'::jsonb),
    ('CI-RETENTION-TASK-5', '{"id":"CI-RETENTION-TASK-5"}'::jsonb)
  on conflict (id) do nothing;

  insert into public.papi_jobs(
    id, task_id, handler, payload, idempotency_key, status,
    created_at, lease_owner, lease_token, lease_until
  ) values
    ('CI-RETENTION-JOB-1', 'CI-RETENTION-TASK-1', 'test.retention', '{}',
     'ci-retention-key-1', 'done', v_cutoff - interval '1 day', null, null, null),
    ('CI-RETENTION-JOB-2', 'CI-RETENTION-TASK-2', 'test.retention', '{}',
     'ci-retention-key-2', 'failed', v_cutoff - interval '2 days', null, null, null),
    ('CI-RETENTION-JOB-3', 'CI-RETENTION-TASK-3', 'test.retention', '{}',
     'ci-retention-key-3', 'queued', v_cutoff - interval '3 days', null, null, null),
    ('CI-RETENTION-JOB-4', 'CI-RETENTION-TASK-4', 'test.retention', '{}',
     'ci-retention-key-4', 'running', v_cutoff - interval '4 days',
     'ci-retention-worker', '00000000-0000-4000-8000-000000000004',
     now() + interval '5 minutes'),
    ('CI-RETENTION-JOB-5', 'CI-RETENTION-TASK-5', 'test.retention', '{}',
     'ci-retention-key-5', 'done', now() - interval '1 day', null, null, null);

  select count(*) into v_before from public.papi_jobs
   where id like 'CI-RETENTION-JOB-%';

  v_preview := public.papi_execution_queue_retention_preview(v_cutoff);

  if v_preview->>'preview_only' <> 'true'
     or (v_preview->>'eligible_done')::integer <> 1
     or (v_preview->>'eligible_failed')::integer <> 1
     or (v_preview->>'protected_running')::integer < 1
     or (v_preview->>'protected_queued_or_retry')::integer < 1
     or (v_preview->>'protected_recent_terminal')::integer < 1 then
    raise exception 'Retention preview classification is incorrect: %', v_preview;
  end if;

  if v_preview::text like '%CI-RETENTION-JOB%'
     or v_preview::text like '%ci-retention-key%'
     or v_preview::text like '%payload%' then
    raise exception 'Retention preview leaked record-level data';
  end if;

  select count(*) into v_after from public.papi_jobs
   where id like 'CI-RETENTION-JOB-%';
  if v_after <> v_before then
    raise exception 'Preview unexpectedly changed the number of jobs';
  end if;

  if not has_function_privilege('service_role',
       'public.papi_execution_queue_retention_preview(timestamp with time zone)', 'execute')
     or has_function_privilege('anon',
       'public.papi_execution_queue_retention_preview(timestamp with time zone)', 'execute')
     or has_function_privilege('authenticated',
       'public.papi_execution_queue_retention_preview(timestamp with time zone)', 'execute') then
    raise exception 'Retention preview function privileges are too broad or incomplete';
  end if;

  begin
    perform public.papi_execution_queue_retention_preview(now() + interval '1 day');
    raise exception 'Future retention cutoff was accepted';
  exception when sqlstate '22023' then
    null;
  end;
end;
$$;
rollback;
