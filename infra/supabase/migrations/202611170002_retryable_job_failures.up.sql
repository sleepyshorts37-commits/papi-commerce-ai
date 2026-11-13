-- Explicitly distinguish transient failures from terminal validation/policy failures.
-- Kept as a new overload so existing four-argument callers remain compatible.
create or replace function public.papi_fail_job(
    p_job_id text,
    p_worker_id text,
    p_lease_token uuid,
    p_error_code text,
    p_retryable boolean
) returns text
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare
    v_job public.papi_jobs%rowtype;
    v_status text;
begin
    if p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}$'
       or p_retryable is null then
        raise exception 'Invalid job failure request' using errcode = '22023';
    end if;

    select * into v_job
      from public.papi_jobs
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now()
     for update;
    if not found then
        raise exception 'Job lease lost or expired' using errcode = '40001';
    end if;

    if not p_retryable or v_job.attempts >= v_job.max_attempts then
        v_status := 'failed';
    else
        v_status := 'retry';
    end if;

    update public.papi_jobs
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => least(3600, 15 * power(2, attempts - 1)::integer))
             else available_at end,
           last_error_code = p_error_code,
           updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id;
    return v_status;
end;
$$;

revoke all on function public.papi_fail_job(text, text, uuid, text, boolean)
    from public, anon, authenticated;
grant execute on function public.papi_fail_job(text, text, uuid, text, boolean)
    to service_role;
