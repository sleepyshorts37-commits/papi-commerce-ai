-- Seed two isolated jobs for the multi-session SKIP LOCKED contract test.
insert into public.papi_tasks(id, task)
values
  ('CI-CONCURRENT-TASK-A', '{"id":"CI-CONCURRENT-TASK-A","owner_agent":"ci-agent"}'::jsonb),
  ('CI-CONCURRENT-TASK-B', '{"id":"CI-CONCURRENT-TASK-B","owner_agent":"ci-agent"}'::jsonb)
on conflict (id) do nothing;

insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, max_attempts)
values
  ('CI-CONCURRENT-JOB-A', 'CI-CONCURRENT-TASK-A', 'test.noop', '{}'::jsonb, 'ci-concurrent-idem-a', 3),
  ('CI-CONCURRENT-JOB-B', 'CI-CONCURRENT-TASK-B', 'test.noop', '{}'::jsonb, 'ci-concurrent-idem-b', 3)
on conflict (id) do nothing;

do $$
begin
  if exists (
    select 1 from public.papi_jobs
     where id in ('CI-CONCURRENT-JOB-A', 'CI-CONCURRENT-JOB-B')
       and status <> 'queued'
  ) then
    raise exception 'Concurrency fixtures must start queued';
  end if;
end;
$$;
