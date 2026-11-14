-- Mission 28 rollback refuses to remove worker assignment history.
begin;
do $guard$
begin
  if exists (select 1 from public.papi_worker_assignments) then
    raise exception 'Refusing worker rollback: assignment history exists';
  end if;
end
$guard$;
drop function if exists public.papi_finish_worker_job(text,text,uuid,boolean,jsonb,text);
drop function if exists public.papi_claim_worker_job(text,uuid,integer);
drop function if exists public.papi_assign_worker_task(text,text,text,text,text,text,jsonb,text);
drop function if exists public.papi_set_worker_status(text,text);
drop function if exists public.papi_register_worker(text,text,text,text,text,text,text[],text[],integer);
drop table if exists public.papi_worker_assignments;
drop table if exists public.papi_workers;
commit;
