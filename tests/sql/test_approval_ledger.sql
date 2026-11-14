-- Mission 26 approval ledger: atomic scope, one-time use, audit and grants.
begin;

insert into public.papi_tasks(id, task, version)
values (
  'TASK-M26-001',
  '{"id":"TASK-M26-001","status":"in_progress","title":"Disposable approval contract test"}'::jsonb,
  1
);

do $issue$
begin
  if not public.papi_issue_approval(
    'APR-M26-0001', 'TASK-M26-001', 'external.email.send',
    'external_communication', 'owner-test',
    now(), now() + interval '10 minutes'
  ) then
    raise exception 'Valid approval issuance returned false';
  end if;
end
$issue$;

do $scope$
begin
  if public.papi_consume_approval(
    'APR-M26-0001', 'TASK-OTHER', 'external.email.send',
    'external_communication', 'agent-test'
  ) then
    raise exception 'Approval accepted for a different task';
  end if;
  if public.papi_consume_approval(
    'APR-M26-0001', 'TASK-M26-001', 'external.social.publish',
    'external_communication', 'agent-test'
  ) then
    raise exception 'Approval accepted for a different handler';
  end if;
  if public.papi_consume_approval(
    'APR-M26-0001', 'TASK-M26-001', 'external.email.send',
    'financial', 'agent-test'
  ) then
    raise exception 'Approval accepted for a different action class';
  end if;
end
$scope$;

do $consume$
begin
  if not public.papi_consume_approval(
    'APR-M26-0001', 'TASK-M26-001', 'external.email.send',
    'external_communication', 'agent-test'
  ) then
    raise exception 'First valid approval consumption failed';
  end if;
  if public.papi_consume_approval(
    'APR-M26-0001', 'TASK-M26-001', 'external.email.send',
    'external_communication', 'agent-test'
  ) then
    raise exception 'Approval was consumed more than once';
  end if;
end
$consume$;

do $audit$
begin
  if (select count(*) from public.papi_audit_events
      where event_id in ('approval-issued:APR-M26-0001','approval-consumed:APR-M26-0001')) <> 2 then
    raise exception 'Approval issue/consume audit events missing';
  end if;
  if (select count(*) from public.papi_approval_ledger
      where approval_id = 'APR-M26-0001' and consumed_at is not null
        and consumed_by = 'agent-test') <> 1 then
    raise exception 'Approval ledger consumption state incorrect';
  end if;
  if has_table_privilege('service_role', 'public.papi_approval_ledger', 'update')
     or has_table_privilege('service_role', 'public.papi_approval_ledger', 'delete')
     or has_table_privilege('anon', 'public.papi_approval_ledger', 'select')
     or has_table_privilege('authenticated', 'public.papi_approval_ledger', 'select')
     or not has_function_privilege('service_role',
       'public.papi_consume_approval(text,text,text,text,text)', 'execute')
     or has_function_privilege('anon',
       'public.papi_consume_approval(text,text,text,text,text)', 'execute')
     or has_function_privilege('authenticated',
       'public.papi_consume_approval(text,text,text,text,text)', 'execute') then
    raise exception 'Approval ledger/function privileges are too broad or incomplete';
  end if;
end
$audit$;

do $invalid$
begin
  begin
    perform public.papi_issue_approval(
      'APR-M26-EXPIRED', 'TASK-M26-001', 'external.email.send',
      'external_communication', 'owner-test',
      now() - interval '1 hour', now() - interval '30 minutes'
    );
    raise exception 'Expired approval issuance was accepted';
  exception when sqlstate '22023' then
    null;
  end;
  begin
    perform public.papi_issue_approval(
      'APR-M26-LONGTTL', 'TASK-M26-001', 'external.email.send',
      'external_communication', 'owner-test',
      now(), now() + interval '16 minutes'
    );
    raise exception 'Overlong approval issuance was accepted';
  exception when sqlstate '22023' then
    null;
  end;
end
$invalid$;

rollback;
