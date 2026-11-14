-- Mission 32 scoped memory visibility and keyset pagination contract.
BEGIN;
do $$
declare
    v_rows record;
    v_count integer;
    v_cursor_time timestamptz;
    v_cursor_id uuid;
    v_rejected boolean := false;
begin
    insert into public.papi_memory_events(
        event_id,memory_id,event_type,created_at,actor,category,title,content,
        source_type,source_id,confidence,scope,tags,sensitivity,idempotency_key
    ) values
    ('10000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','remember','2026-11-14T10:00:00Z','marietou','fact','Shared fact','Visible to all','test','shared-1',0.9,'shared',array['shared'],'normal','m32-shared-key-0001'),
    ('10000000-0000-4000-8000-000000000002','20000000-0000-4000-8000-000000000002','remember','2026-11-14T10:01:00Z','astou','fact','Private fact','Visible to Astou','test','private-1',0.9,'agent',array['private'],'normal','m32-private-key-0001'),
    ('10000000-0000-4000-8000-000000000003','20000000-0000-4000-8000-000000000003','remember','2026-11-14T10:02:00Z','marietou','fact','Other private fact','Not visible to Astou','test','private-2',0.9,'agent',array['private'],'normal','m32-private-key-0002');

    insert into public.papi_memory_events(
        event_id,memory_id,event_type,created_at,actor,target_memory_id,reason,tags,idempotency_key
    ) values (
        '10000000-0000-4000-8000-000000000004','20000000-0000-4000-8000-000000000001',
        'supersede','2026-11-14T10:03:00Z','marietou',
        '20000000-0000-4000-8000-000000000001','Updated shared fact',array[]::text[],'m32-supersede-key-001'
    );

    select count(*) into v_count from public.papi_list_memory_events('astou', null, null, 10);
    if v_count <> 3 then
        raise exception 'Expected shared, own-agent and shared supersede events; got %', v_count;
    end if;
    if exists (
        select 1 from public.papi_list_memory_events('astou', null, null, 10)
        where event_id = '10000000-0000-4000-8000-000000000003'
    ) then
        raise exception 'Private memory from another agent leaked';
    end if;
    select created_at,event_id into v_cursor_time,v_cursor_id
    from public.papi_list_memory_events('astou', null, null, 2)
    order by created_at asc,event_id asc limit 1;
    select count(*) into v_count
    from public.papi_list_memory_events('astou',v_cursor_time,v_cursor_id,10);
    if v_count <> 1 then
        raise exception 'Keyset pagination did not return the remaining visible event';
    end if;
    begin
        perform * from public.papi_list_memory_events('astou', null, '10000000-0000-4000-8000-000000000001', 10);
    exception when invalid_parameter_value then
        v_rejected := true;
    end;
    if not v_rejected then raise exception 'Partial cursor was accepted'; end if;
    if has_function_privilege('anon','public.papi_list_memory_events(text,timestamptz,uuid,integer)','execute')
       or has_function_privilege('authenticated','public.papi_list_memory_events(text,timestamptz,uuid,integer)','execute')
       or not has_function_privilege('service_role','public.papi_list_memory_events(text,timestamptz,uuid,integer)','execute') then
        raise exception 'Memory reader privileges are incorrect';
    end if;
end;
$$;
ROLLBACK;
