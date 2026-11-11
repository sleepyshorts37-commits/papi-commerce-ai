-- PAPI COMMERCE AI — Supabase / PostgreSQL
-- Exécuter dans l'éditeur SQL du projet Supabase.
-- Les tables ne sont accessibles ni à anon ni à authenticated.
-- Le backend doit utiliser une clé serveur conservée uniquement dans ses secrets.

create table if not exists public.papi_tasks (
    id text primary key,
    task jsonb not null check (jsonb_typeof(task) = 'object'),
    version bigint not null default 1 check (version >= 1),
    updated_at timestamptz not null default now()
);

create table if not exists public.papi_audit_events (
    event_id text primary key,
    occurred_at timestamptz not null,
    actor text not null,
    action text not null,
    entity_type text not null,
    entity_id text not null,
    details jsonb not null default '{}'::jsonb check (jsonb_typeof(details) = 'object')
);

create index if not exists papi_tasks_updated_at_idx on public.papi_tasks(updated_at);
create index if not exists papi_audit_entity_idx on public.papi_audit_events(entity_type, entity_id);

alter table public.papi_tasks enable row level security;
alter table public.papi_audit_events enable row level security;

revoke all on public.papi_tasks from anon, authenticated;
revoke all on public.papi_audit_events from anon, authenticated;
grant select, insert, update on public.papi_tasks to service_role;
grant select, insert on public.papi_audit_events to service_role;

-- Une transition et son événement sont validés ou annulés ensemble.
-- Le contrôle de version empêche deux agents d'écraser une modification concurrente.
create or replace function public.papi_commit_task_change(
    p_task_id text,
    p_expected_version bigint,
    p_task jsonb,
    p_event jsonb
) returns bigint
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_new_version bigint;
begin
    if p_task_id is null or length(trim(p_task_id)) = 0
       or jsonb_typeof(p_task) <> 'object'
       or p_task->>'id' is distinct from p_task_id
       or jsonb_typeof(p_event) <> 'object'
       or p_event->>'entity_type' is distinct from 'task'
       or p_event->>'entity_id' is distinct from p_task_id
       or p_event->>'event_id' is null
       or p_event->>'occurred_at' is null
       or p_event->>'actor' is null
       or p_event->>'action' is null
       or jsonb_typeof(p_event->'details') <> 'object'
       or p_expected_version < 1 then
        raise exception 'Invalid task change payload' using errcode = '22023';
    end if;

    update public.papi_tasks
       set task = p_task,
           version = version + 1,
           updated_at = now()
     where id = p_task_id
       and version = p_expected_version
    returning version into v_new_version;

    if v_new_version is null then
        raise exception 'Task version conflict or task not found' using errcode = '40001';
    end if;

    insert into public.papi_audit_events (
        event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
        p_event->>'event_id',
        (p_event->>'occurred_at')::timestamptz,
        p_event->>'actor',
        p_event->>'action',
        p_event->>'entity_type',
        p_event->>'entity_id',
        p_event->'details'
    );

    return v_new_version;
end;
$$;

revoke all on function public.papi_commit_task_change(text, bigint, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.papi_commit_task_change(text, bigint, jsonb, jsonb) to service_role;
