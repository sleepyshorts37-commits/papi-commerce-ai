-- Mission 32: scoped, keyset-paginated shared-memory event reader.
create or replace function public.papi_list_memory_events(
    p_actor text,
    p_before_created_at timestamptz default null,
    p_before_event_id uuid default null,
    p_limit integer default 50
)
returns table (
    event_id uuid, memory_id uuid, event_type text, created_at timestamptz,
    actor text, category text, title text, content text, source_type text,
    source_id text, confidence numeric, scope text, tags text[],
    sensitivity text, target_memory_id uuid, reason text
)
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $$
begin
    if p_actor is null or p_actor !~ '^[A-Za-z0-9_-]{1,100}$' then
        raise exception 'Invalid memory actor' using errcode = '22023';
    end if;
    if p_limit is null or p_limit not between 1 and 101 then
        raise exception 'Memory page limit must be between 1 and 101' using errcode = '22023';
    end if;
    if (p_before_created_at is null) <> (p_before_event_id is null) then
        raise exception 'Both memory cursor fields must be supplied together' using errcode = '22023';
    end if;

    return query
    select e.event_id, e.memory_id, e.event_type, e.created_at, e.actor,
           e.category, e.title, e.content, e.source_type, e.source_id,
           e.confidence, e.scope, e.tags, e.sensitivity, e.target_memory_id, e.reason
    from public.papi_memory_events e
    where (
        (e.event_type = 'remember' and
            (e.scope = 'shared' or (e.scope = 'agent' and e.actor = p_actor)))
        or
        (e.event_type = 'supersede' and exists (
            select 1 from public.papi_memory_events target
            where target.memory_id = e.target_memory_id
              and target.event_type = 'remember'
              and (target.scope = 'shared' or (target.scope = 'agent' and target.actor = p_actor))
        ))
    )
    and (p_before_created_at is null or
         (e.created_at, e.event_id) < (p_before_created_at, p_before_event_id))
    order by e.created_at desc, e.event_id desc
    limit p_limit;
end;
$$;

revoke all on function public.papi_list_memory_events(text,timestamptz,uuid,integer)
    from public, anon, authenticated;
grant execute on function public.papi_list_memory_events(text,timestamptz,uuid,integer)
    to service_role;
