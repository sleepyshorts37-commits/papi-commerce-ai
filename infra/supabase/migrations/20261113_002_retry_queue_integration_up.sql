-- Migration 20261113_002: integrate bounded retry decisions with the durable queue.
-- Apply only to a disposable/test database first. Re-applicable and additive.
BEGIN;

create or replace function public.papi_fail_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_error_code text,
    p_retry_allowed boolean, p_retry_delay_seconds integer
) returns text
language plpgsql security invoker
set search_path = public, pg_temp
as $retry$
declare
    v_job public.papi_jobs%rowtype;
    v_status text;
begin
    if p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}$'
       or p_retry_allowed is null
       or p_retry_delay_seconds is null
       or p_retry_delay_seconds < 0 or p_retry_delay_seconds > 3600
       or (not p_retry_allowed and p_retry_delay_seconds <> 0)
       or (p_retry_allowed and p_error_code not in (
           'temporarily_unavailable', 'rate_limited',
           'connection_reset', 'service_timeout'
       )) then
        raise exception 'Invalid retry decision' using errcode = '22023';
    end if;

    select * into v_job from public.papi_jobs
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now()
     for update;
    if not found then
        raise exception 'Job lease lost or expired' using errcode = '40001';
    end if;

    if p_retry_allowed and v_job.attempts < v_job.max_attempts then
        v_status := 'retry';
    else
        v_status := 'failed';
    end if;

    update public.papi_jobs
       set status = v_status,
           available_at = case when v_status = 'retry'
             then now() + make_interval(secs => p_retry_delay_seconds)
             else available_at end,
           last_error_code = p_error_code,
           updated_at = now(),
           lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id;
    return v_status;
end;
$retry$;

revoke all on function public.papi_fail_job(text, text, uuid, text, boolean, integer)
    from public, anon, authenticated;
grant execute on function public.papi_fail_job(text, text, uuid, text, boolean, integer)
    to service_role;

COMMIT;
