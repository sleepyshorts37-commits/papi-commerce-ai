-- Mission 31: shared, read-only operational command-center snapshot.
create or replace function public.papi_command_center_snapshot(p_limit integer default 20)
returns jsonb language plpgsql stable security invoker
set search_path = public, pg_temp as $$
declare v_snapshot jsonb;
begin
    if p_limit is null or p_limit not between 1 and 100 then
        raise exception 'Command-center limit must be between 1 and 100' using errcode = '22023';
    end if;
    select jsonb_build_object(
        'generated_at', now(),
        'summary', jsonb_build_object(
            'workers_total', (select count(*) from public.papi_workers),
            'workers_active', (select count(*) from public.papi_workers where status = 'active'),
            'workers_paused', (select count(*) from public.papi_workers where status = 'paused'),
            'workers_disabled', (select count(*) from public.papi_workers where status = 'disabled'),
            'tasks_total', (select count(*) from public.papi_tasks),
            'jobs_queued', (select count(*) from public.papi_jobs where status = 'queued'),
            'jobs_running', (select count(*) from public.papi_jobs where status = 'running'),
            'jobs_retry', (select count(*) from public.papi_jobs where status = 'retry'),
            'jobs_failed', (select count(*) from public.papi_jobs where status = 'failed'),
            'jobs_done', (select count(*) from public.papi_jobs where status = 'done'),
            'alerts_open', (select count(*) from public.papi_supervisor_alerts where status = 'open'),
            'alerts_acknowledged', (select count(*) from public.papi_supervisor_alerts where status = 'acknowledged'),
            'incidents_open', (select count(*) from public.papi_incidents where status not in ('resolved','closed')),
            'incidents_overdue', (select count(*) from public.papi_incidents where status not in ('resolved','closed') and target_resolution_at < now()),
            'outbox_pending', (select count(*) from public.papi_outbox where status = 'pending'),
            'outbox_processing', (select count(*) from public.papi_outbox where status = 'processing'),
            'outbox_retry', (select count(*) from public.papi_outbox where status = 'retry'),
            'outbox_dead_letter', (select count(*) from public.papi_outbox where status = 'dead_letter'),
            'approvals_active', (select count(*) from public.papi_approval_ledger where consumed_at is null and expires_at > now()),
            'approvals_consumed', (select count(*) from public.papi_approval_ledger where consumed_at is not null),
            'approvals_expired', (select count(*) from public.papi_approval_ledger where consumed_at is null and expires_at <= now())
        ),
        'workers', coalesce((select jsonb_agg(to_jsonb(x) order by x.worker_id) from (
            select w.worker_id, w.display_name, w.department, w.role_name, w.manager_worker_id,
                   w.status, w.max_concurrency, h.last_seen_at as heartbeat_at, h.source as heartbeat_source
            from public.papi_workers w left join public.papi_worker_heartbeats h using(worker_id)
            order by w.updated_at desc, w.worker_id limit p_limit
        ) x), '[]'::jsonb),
        'jobs', coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc) from (
            select j.id, j.task_id, j.handler, j.status, j.attempts, j.max_attempts,
                   j.available_at, j.lease_until, j.last_error_code, j.created_at, j.updated_at
            from public.papi_jobs j order by j.created_at desc limit p_limit
        ) x), '[]'::jsonb),
        'assignments', coalesce((select jsonb_agg(to_jsonb(x) order by x.assigned_at desc) from (
            select a.assignment_id, a.task_id, a.worker_id, a.job_id, a.required_skill,
                   a.status, a.assigned_at, a.started_at, a.finished_at
            from public.papi_worker_assignments a order by a.assigned_at desc limit p_limit
        ) x), '[]'::jsonb),
        'alerts', coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc) from (
            select a.alert_id, a.worker_id, a.manager_worker_id, a.severity, a.alert_type,
                   a.status, a.summary, a.recommended_action, a.created_at
            from public.papi_supervisor_alerts a order by a.created_at desc limit p_limit
        ) x), '[]'::jsonb),
        'incidents', coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc) from (
            select i.incident_id, i.incident_key, i.worker_id, i.job_id, i.category, i.severity,
                   i.status, i.title, i.assigned_human, i.created_at, i.target_resolution_at,
                   i.sla_breached_at, i.resolved_at, i.closed_at
            from public.papi_incidents i order by i.created_at desc limit p_limit
        ) x), '[]'::jsonb)
    ) into v_snapshot;
    return v_snapshot;
end;
$$;
revoke all on function public.papi_command_center_snapshot(integer) from public, anon, authenticated;
grant execute on function public.papi_command_center_snapshot(integer) to service_role;
