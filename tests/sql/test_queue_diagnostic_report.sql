-- Diagnostic report is aggregate-only and does not mutate queue records.
begin;
do $$
declare
  v_report jsonb;
  v_before bigint;
  v_after bigint;
  v_cutoff timestamptz := now() - interval '30 days';
begin
  select count(*) into v_before from public.papi_jobs;
  v_report := public.papi_execution_queue_diagnostic_report(v_cutoff);
  select count(*) into v_after from public.papi_jobs;

  if v_report->>'report_version' <> '1'
     or v_report->>'manual_action_required' <> 'true'
     or v_report->>'automated_recovery_enabled' <> 'false'
     or jsonb_typeof(v_report->'queue_health') <> 'object'
     or jsonb_typeof(v_report->'error_summary') <> 'object'
     or jsonb_typeof(v_report->'retention_preview') <> 'object'
     or v_report->'retention_preview'->>'preview_only' <> 'true' then
    raise exception 'Diagnostic report missing required safe sections: %', v_report;
  end if;

  if v_report::text like '%lease_token%'
     or v_report::text like '%idempotency_key%'
     or v_report::text like '%last_error_code%'
     or v_report::text like '%payload%'
     or v_report::text like '%result%' then
    raise exception 'Diagnostic report leaked record-level or sensitive fields';
  end if;

  if v_after <> v_before then
    raise exception 'Diagnostic report unexpectedly changed queue records';
  end if;

  if not has_function_privilege('service_role',
       'public.papi_execution_queue_diagnostic_report(timestamp with time zone)', 'execute')
     or has_function_privilege('anon',
       'public.papi_execution_queue_diagnostic_report(timestamp with time zone)', 'execute')
     or has_function_privilege('authenticated',
       'public.papi_execution_queue_diagnostic_report(timestamp with time zone)', 'execute') then
    raise exception 'Diagnostic report function privileges are too broad or incomplete';
  end if;

  begin
    perform public.papi_execution_queue_diagnostic_report(now() + interval '1 day');
    raise exception 'Future diagnostic cutoff was accepted';
  exception when sqlstate '22023' then
    null;
  end;
end;
$$;
rollback;
