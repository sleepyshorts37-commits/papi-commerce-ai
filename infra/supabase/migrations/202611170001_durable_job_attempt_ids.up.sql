-- PAPI: durable identity and history for every effective job reservation.
-- Additive and safe for existing jobs. Existing history is necessarily reconstructed
-- as one legacy snapshot because the old schema retained only the attempts counter.

alter table public.papi_jobs
    add column if not exists current_attempt_id uuid;

create table if not exists public.papi_job_attempts (
    attempt_id uuid primary key,
    job_id text not null references public.papi_jobs(id) on delete restrict,
    attempt_number integer not null check (attempt_number > 0),
    worker_id text,
    lease_token uuid,
    status text not null check (status in ('running', 'retry', 'completed', 'failed', 'lease_expired')),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    error_code text,
    is_legacy boolean not null default false,
    unique (job_id, attempt_number),
    check ((status = 'running') = (finished_at is null))
);

-- Preserve the latest known attempt for jobs created before this migration.
with legacy as (
    select id as job_id, attempts as attempt_number, gen_random_uuid() as attempt_id,
           coalesce(lease_owner, 'legacy-unknown') as worker_id,
           lease_token,
           case
             when status = 'running' then 'running'
             when status = 'done' then 'completed'
             when status = 'failed' then 'failed'
             else 'retry'
           end as attempt_status,
           case when status = 'running' then null else updated_at end as finished_at,
           updated_at as started_at
      from public.papi_jobs
     where attempts > 0
)
insert into public.papi_job_attempts
    (attempt_id, job_id, attempt_number, worker_id, lease_token, status, started_at, finished_at, is_legacy)
select attempt_id, job_id, attempt_number, worker_id, lease_token, attempt_status,
       started_at, finished_at, true
  from legacy
on conflict (job_id, attempt_number) do nothing;

update public.papi_jobs j
   set current_attempt_id = a.attempt_id
  from public.papi_job_attempts a
 where a.job_id = j.id
   and a.attempt_number = j.attempts
   and j.current_attempt_id is null;

alter table public.papi_jobs
    add constraint papi_jobs_current_attempt_fk
    foreign key (current_attempt_id)
    references public.papi_job_attempts(attempt_id)
    deferrable initially deferred;

create index if not exists papi_job_attempts_job_started_idx
    on public.papi_job_attempts(job_id, started_at desc);
create index if not exists papi_job_attempts_status_idx
    on public.papi_job_attempts(status, started_at);

alter table public.papi_job_attempts enable row level security;
revoke all on public.papi_job_attempts from public, anon, authenticated;
grant select, insert, update on public.papi_job_attempts to service_role;

create or replace function public.papi_sync_job_attempt()
returns trigger
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
begin
    if old.current_attempt_id is not null
       and new.current_attempt_id is distinct from old.current_attempt_id then
        update public.papi_job_attempts
           set status = 'lease_expired', finished_at = coalesce(finished_at, now()),
               error_code = coalesce(error_code, 'lease_replaced')
         where attempt_id = old.current_attempt_id and status = 'running';
    elsif old.status = 'running' and new.status in ('done', 'retry', 'failed') then
        update public.papi_job_attempts
           set status = case new.status
                          when 'done' then 'completed'
                          when 'retry' then 'retry'
                          else 'failed'
                        end,
               finished_at = coalesce(finished_at, now()),
               error_code = case when new.status = 'failed' then new.last_error_code else error_code end
         where attempt_id = old.current_attempt_id and status = 'running';
    end if;
    return new;
end;
$$;

drop trigger if exists papi_jobs_sync_attempt on public.papi_jobs;
create trigger papi_jobs_sync_attempt
after update of status, current_attempt_id on public.papi_jobs
for each row execute function public.papi_sync_job_attempt();

create or replace function public.papi_claim_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare
    v_job public.papi_jobs%rowtype;
    v_attempt_id uuid;
    v_attempt_number integer;
begin
    update public.papi_jobs
       set status = 'failed', last_error_code = 'lease_expired_max_attempts',
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where status = 'running' and lease_until < now() and attempts >= max_attempts;

    if p_worker_id is null or length(trim(p_worker_id)) = 0 or length(p_worker_id) > 120
       or p_lease_token is null or p_lease_seconds is null
       or p_lease_seconds < 15 or p_lease_seconds > 900 then
        raise exception 'Invalid worker lease request' using errcode = '22023';
    end if;

    select * into v_job
      from public.papi_jobs
     where attempts < max_attempts
       and ((status in ('queued', 'retry') and available_at <= now())
         or (status = 'running' and lease_until < now()))
     order by available_at, created_at
     for update skip locked
     limit 1;
    if not found then return null; end if;

    v_attempt_id := gen_random_uuid();
    v_attempt_number := v_job.attempts + 1;

    insert into public.papi_job_attempts
        (attempt_id, job_id, attempt_number, worker_id, lease_token, status)
    values
        (v_attempt_id, v_job.id, v_attempt_number, p_worker_id, p_lease_token, 'running');

    update public.papi_jobs
       set status = 'running',
           attempts = v_attempt_number,
           current_attempt_id = v_attempt_id,
           lease_owner = p_worker_id,
           lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;

    return jsonb_build_object(
        'id', v_job.id, 'task_id', v_job.task_id, 'handler', v_job.handler,
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity,
        'attempts', v_job.attempts, 'attempt_id', v_job.current_attempt_id,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
end;
$$;

revoke all on function public.papi_sync_job_attempt() from public, anon, authenticated;
revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
