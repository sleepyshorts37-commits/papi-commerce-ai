-- PAPI COMMAND CENTER 1.3 — snapshot cohérent en une seule transaction de lecture.
-- STABLE : les lectures partagent le snapshot MVCC de la requête appelante.
-- SECURITY INVOKER : les droits RLS/SQL de l'appelant restent applicables.
create or replace function public.papi_get_dashboard_snapshot(
    p_task_limit integer default 10000,
    p_event_limit integer default 10000
) returns jsonb
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $$
declare
    v_tasks jsonb;
    v_events jsonb;
    v_tasks_truncated boolean;
    v_events_truncated boolean;
begin
    if p_task_limit is null or p_task_limit < 1 or p_task_limit > 20000
       or p_event_limit is null or p_event_limit < 1 or p_event_limit > 20000 then
        raise exception 'Invalid dashboard snapshot limits' using errcode = '22023';
    end if;

    select
        coalesce(jsonb_agg(to_jsonb(t) order by t.id), '[]'::jsonb),
        count(*) > p_task_limit
    into v_tasks, v_tasks_truncated
    from (
        select id, task, version
        from public.papi_tasks
        order by id
        limit p_task_limit + 1
    ) as t;

    -- Retirer la ligne sentinelle éventuelle sans perdre l'ordre.
    if v_tasks_truncated then
        select coalesce(jsonb_agg(value order by value->>'id'), '[]'::jsonb)
          into v_tasks
          from jsonb_array_elements(v_tasks) as item(value)
         where value->>'id' in (
             select id from public.papi_tasks order by id limit p_task_limit
         );
    end if;

    select
        coalesce(jsonb_agg(to_jsonb(e) order by e.occurred_at, e.event_id), '[]'::jsonb),
        count(*) > p_event_limit
    into v_events, v_events_truncated
    from (
        select event_id, occurred_at, actor, action, entity_type, entity_id, details
        from public.papi_audit_events
        order by occurred_at, event_id
        limit p_event_limit + 1
    ) as e;

    if v_events_truncated then
        select coalesce(jsonb_agg(value order by value->>'occurred_at', value->>'event_id'), '[]'::jsonb)
          into v_events
          from jsonb_array_elements(v_events) as item(value)
         where value->>'event_id' in (
             select event_id from public.papi_audit_events
             order by occurred_at, event_id limit p_event_limit
         );
    end if;

    return jsonb_build_object(
        'tasks', v_tasks,
        'audit_events', v_events,
        'tasks_truncated', v_tasks_truncated,
        'audit_events_truncated', v_events_truncated,
        'snapshot_consistency', 'single_statement_snapshot'
    );
end;
$$;

revoke all on function public.papi_get_dashboard_snapshot(integer, integer)
    from public, anon, authenticated;
grant execute on function public.papi_get_dashboard_snapshot(integer, integer)
    to service_role;
