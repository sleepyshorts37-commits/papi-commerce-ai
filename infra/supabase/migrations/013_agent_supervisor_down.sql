-- Refuse to destroy supervision history.
do $$ begin
 if exists(select 1 from public.papi_worker_evaluations) or exists(select 1 from public.papi_supervisor_alerts)
 or exists(select 1 from public.papi_worker_heartbeats) then raise exception 'Refusing rollback: supervision history exists'; end if;
end; $$;
drop function if exists public.papi_supervisor_update_alert(uuid,text,text);
drop function if exists public.papi_supervisor_detect_stale_workers(text,integer);
drop function if exists public.papi_supervisor_evaluate_worker(text,text,timestamptz,timestamptz);
drop function if exists public.papi_supervisor_heartbeat(text,text);
drop table if exists public.papi_supervisor_alerts;
drop table if exists public.papi_worker_evaluations;
drop table if exists public.papi_worker_heartbeats;
