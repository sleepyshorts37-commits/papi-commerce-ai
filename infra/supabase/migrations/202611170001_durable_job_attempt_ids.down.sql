drop function if exists public.papi_renew_job(text, text, uuid, integer);
-- Rollback for 202611170001_durable_job_attempt_ids.
-- Existing jobs and their original attempts counter are preserved.
drop trigger if exists papi_jobs_sync_attempt on public.papi_jobs;
drop function if exists public.papi_sync_job_attempt();
alter table public.papi_jobs drop constraint if exists papi_jobs_current_attempt_fk;
alter table public.papi_jobs drop column if exists current_attempt_id;
drop table if exists public.papi_job_attempts;

create or replace function public.papi_claim_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_job public.papi_jobs%rowtype;
begin
    update public.papi_jobs
       set status = 'failed', last_error_code = 'lease_expired_max_attempts',
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where status = 'running' and lease_until < now() and attempts >= max_attempts;

    if p_worker_id is null or length(trim(p_worker_id)) = 0 or length(p_worker_id) > 120
       or p_lease_token is null or p_lease_seconds < 15 or p_lease_seconds > 900 then
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
    update public.papi_jobs
       set status = 'running',
           attempts = attempts + 1,
           lease_owner = p_worker_id,
           lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;
    return jsonb_build_object(
        'id', v_job.id, 'task_id', v_job.task_id, 'handler', v_job.handler,
        'payload', v_job.payload, 'agent_identity', v_job.agent_identity, 'attempts', v_job.attempts,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
end;
$$;

revoke all on function public.papi_claim_job(text, uuid, integer) from public, anon, authenticated;
grant execute on function public.papi_claim_job(text, uuid, integer) to service_role;
