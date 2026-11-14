-- Day 4: safe aggregate diagnostic bundle. No row-level data or recovery side effects.
create or replace function public.papi_execution_queue_diagnostic_report(
    p_retention_cutoff timestamptz
) returns jsonb
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $$
begin
    if p_retention_cutoff is null or p_retention_cutoff >= now() then
        raise exception 'Diagnostic retention cutoff must be in the past'
            using errcode = '22023';
    end if;

    return jsonb_build_object(
        'report_version', 1,
        'generated_at', now(),
        'queue_health', public.papi_execution_queue_health(),
        'error_summary', public.papi_execution_queue_error_summary(),
        'retention_preview', public.papi_execution_queue_retention_preview(p_retention_cutoff),
        'manual_action_required', true,
        'automated_recovery_enabled', false
    );
end;
$$;

revoke all on function public.papi_execution_queue_diagnostic_report(timestamptz)
    from public, anon, authenticated;
grant execute on function public.papi_execution_queue_diagnostic_report(timestamptz)
    to service_role;
