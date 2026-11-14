-- Mission 33 scoped sync approval: exact plan digest, destination and action set.
begin;
insert into public.papi_tasks(id, task, version)
values ('TASK-M33-001',
        '{"id":"TASK-M33-001","status":"in_progress","title":"Sync approval test"}'::jsonb, 1);

do $issue$
begin
  if not public.papi_issue_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','internal_write',
    'owner-test',now(),now()+interval '10 minutes',repeat('a',64),'instance-b',
    jsonb_build_array(repeat('b',64),repeat('c',64))
  ) then raise exception 'Scoped sync approval issuance failed'; end if;
end
$issue$;

do $scope$
begin
  if public.papi_consume_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','worker-test',
    repeat('d',64),'instance-b',jsonb_build_array(repeat('b',64),repeat('c',64))
  ) then raise exception 'Wrong digest was accepted'; end if;
  if public.papi_consume_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','worker-test',
    repeat('a',64),'instance-c',jsonb_build_array(repeat('b',64),repeat('c',64))
  ) then raise exception 'Wrong destination was accepted'; end if;
  if public.papi_consume_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','worker-test',
    repeat('a',64),'instance-b',jsonb_build_array(repeat('b',64))
  ) then raise exception 'Partial action set was accepted'; end if;
end
$scope$;

do $consume$
begin
  if not public.papi_consume_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','worker-test',
    repeat('a',64),'instance-b',jsonb_build_array(repeat('b',64),repeat('c',64))
  ) then raise exception 'Exact scoped approval was not consumed'; end if;
  if public.papi_consume_sync_approval(
    'APR-M33-0001','TASK-M33-001','sync.apply_plan','worker-test',
    repeat('a',64),'instance-b',jsonb_build_array(repeat('b',64),repeat('c',64))
  ) then raise exception 'Scoped approval replay succeeded'; end if;
end
$consume$;

do $invalid_scope$
begin
  begin
    perform public.papi_issue_sync_approval(
      'APR-M33-NULL01','TASK-M33-001','sync.apply_plan','internal_write',
      'owner-test',now(),now()+interval '5 minutes',repeat('a',64),'instance-b',null
    );
    raise exception 'Null action list was accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.papi_issue_sync_approval(
      'APR-M33-DUP001','TASK-M33-001','sync.apply_plan','internal_write',
      'owner-test',now(),now()+interval '5 minutes',repeat('a',64),'instance-b',
      jsonb_build_array(repeat('b',64),repeat('b',64))
    );
    raise exception 'Duplicate action IDs were accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.papi_issue_sync_approval(
      'APR-M33-BAD001','TASK-M33-001','sync.apply_plan','internal_write',
      'owner-test',now(),now()+interval '5 minutes',repeat('a',64),'instance-b',
      jsonb_build_array('not-a-digest')
    );
    raise exception 'Malformed action ID was accepted';
  exception when sqlstate '22023' then null;
  end;
end
$invalid_scope$;

do $audit$
begin
  if (select count(*) from public.papi_audit_events
      where event_id in ('sync-approval-issued:APR-M33-0001',
                         'sync-approval-consumed:APR-M33-0001')) <> 2 then
    raise exception 'Scoped sync approval audit missing';
  end if;
  if has_function_privilege('anon',
       'public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb)','execute')
     or has_function_privilege('authenticated',
       'public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb)','execute')
     or not has_function_privilege('service_role',
       'public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb)','execute') then
    raise exception 'Scoped approval function grants are incorrect';
  end if;
end
$audit$;
rollback;
