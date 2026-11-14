-- Mission 33: approval ledger scope bound to immutable sync-plan digest.
begin;

alter table public.papi_approval_ledger
    add column if not exists scope_digest text,
    add column if not exists destination_instance text,
    add column if not exists action_ids jsonb;

alter table public.papi_approval_ledger
    drop constraint if exists papi_approval_sync_scope_check;
alter table public.papi_approval_ledger
    add constraint papi_approval_sync_scope_check check (
      (scope_digest is null and destination_instance is null and action_ids is null)
      or
      (scope_digest ~ '^[a-f0-9]{64}$'
       and destination_instance ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
       and jsonb_typeof(action_ids) = 'array'
       and jsonb_array_length(action_ids) between 1 and 500)
    );

create or replace function public.papi_issue_sync_approval(
    p_approval_id text, p_task_id text, p_handler text, p_action_class text,
    p_approved_by text, p_approved_at timestamptz, p_expires_at timestamptz,
    p_scope_digest text, p_destination_instance text, p_action_ids jsonb
) returns boolean
language plpgsql security definer
set search_path = public, pg_temp
as $$
begin
    if p_scope_digest is null or p_scope_digest !~ '^[a-f0-9]{64}$'
       or p_destination_instance is null
       or p_destination_instance !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
       or jsonb_typeof(p_action_ids) <> 'array'
       or jsonb_array_length(p_action_ids) not between 1 and 500
       or exists (select 1 from jsonb_array_elements_text(p_action_ids) x
                  where x !~ '^[a-f0-9]{64}$')
       or (select count(*) from jsonb_array_elements_text(p_action_ids))
          <> (select count(distinct value) from jsonb_array_elements_text(p_action_ids) as ids(value)) then
        raise exception 'Invalid sync approval scope' using errcode = '22023';
    end if;
    if p_approval_id is null or p_approval_id !~ '^[A-Za-z0-9_-]{8,120}$'
       or p_task_id is null or length(trim(p_task_id)) = 0
       or p_handler is null or length(trim(p_handler)) not between 1 and 100
       or p_action_class is distinct from 'internal_write'
       or p_approved_by is null or length(trim(p_approved_by)) not between 1 and 120
       or p_approved_at is null or p_expires_at is null
       or p_approved_at > now() + interval '60 seconds'
       or p_expires_at <= now() or p_expires_at <= p_approved_at
       or p_expires_at - p_approved_at > interval '15 minutes' then
        raise exception 'Invalid sync approval issuance' using errcode = '22023';
    end if;

    insert into public.papi_approval_ledger(
      approval_id, task_id, handler, action_class, approved_by, approved_at, expires_at,
      scope_digest, destination_instance, action_ids
    ) values (
      p_approval_id, p_task_id, p_handler, p_action_class, p_approved_by,
      p_approved_at, p_expires_at, p_scope_digest, p_destination_instance, p_action_ids
    );

    insert into public.papi_audit_events(
      event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
      'sync-approval-issued:' || p_approval_id, now(), p_approved_by,
      'sync_approval.issued', 'sync_approval', p_approval_id,
      jsonb_build_object('plan_digest', p_scope_digest,
                         'destination_instance', p_destination_instance,
                         'action_count', jsonb_array_length(p_action_ids))
    );
    return true;
end;
$$;

create or replace function public.papi_consume_sync_approval(
    p_approval_id text, p_task_id text, p_handler text, p_consumer_id text,
    p_scope_digest text, p_destination_instance text, p_action_ids jsonb
) returns boolean
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare v_approved_by text;
begin
    if p_scope_digest is null or p_scope_digest !~ '^[a-f0-9]{64}$'
       or p_destination_instance is null
       or jsonb_typeof(p_action_ids) <> 'array' then
        raise exception 'Invalid sync approval consumption scope' using errcode = '22023';
    end if;
    update public.papi_approval_ledger
       set consumed_at = now(), consumed_by = p_consumer_id
     where approval_id = p_approval_id
       and task_id = p_task_id and handler = p_handler
       and action_class = 'internal_write'
       and scope_digest = p_scope_digest
       and destination_instance = p_destination_instance
       and action_ids = p_action_ids
       and consumed_at is null and expires_at > now()
    returning approved_by into v_approved_by;

    if v_approved_by is null then return false; end if;
    insert into public.papi_audit_events(
      event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
      'sync-approval-consumed:' || p_approval_id, now(), p_consumer_id,
      'sync_approval.consumed', 'sync_approval', p_approval_id,
      jsonb_build_object('plan_digest', p_scope_digest,
                         'destination_instance', p_destination_instance,
                         'approved_by', v_approved_by)
    );
    return true;
end;
$$;

revoke all on function public.papi_issue_sync_approval(text,text,text,text,text,timestamptz,timestamptz,text,text,jsonb)
    from public, anon, authenticated;
revoke all on function public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb)
    from public, anon, authenticated;
grant execute on function public.papi_issue_sync_approval(text,text,text,text,text,timestamptz,timestamptz,text,text,jsonb)
    to service_role;
grant execute on function public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb)
    to service_role;

commit;
