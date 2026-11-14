-- Observability-only performance probe. Run after migrations 006-009 on disposable PostgreSQL.
-- EXPLAIN ANALYZE executes only stable read functions; no queue mutation occurs.
\echo 'PLAN: queue health aggregate'
explain (analyze, buffers, format json)
select public.papi_execution_queue_health();

\echo 'PLAN: generic error summary'
explain (analyze, buffers, format json)
select public.papi_execution_queue_error_summary();

\echo 'PLAN: diagnostic aggregate'
explain (analyze, buffers, format json)
select public.papi_execution_queue_diagnostic_report(now() - interval '30 days');

-- Guard that the probes did not mutate queue cardinality.
do $$
declare
  v_before bigint;
  v_after bigint;
begin
  select count(*) into v_before from public.papi_jobs;
  perform public.papi_execution_queue_health();
  perform public.papi_execution_queue_error_summary();
  perform public.papi_execution_queue_diagnostic_report(now() - interval '30 days');
  select count(*) into v_after from public.papi_jobs;
  if v_before <> v_after then
    raise exception 'Read-only performance probes changed queue cardinality';
  end if;
end;
$$;
