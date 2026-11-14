-- Mission 26: durable, scoped, one-time human approvals.
-- No external action is executed by these functions.

create table if not exists public.papi_approval_ledger (
    approval_id text primary key check (approval_id ~ '^[A-Za-z0-9_-]{8,120}$'),
    task_id text not null references public.papi_tasks(id) on delete restrict,
    handler text not null check (length(handler) between 1 and 100),
    action_class text not null check (
        action_class in ('read_only', 'internal_write', 'external_communication', 'financial', 'legal')
    ),
    approved_by text not null check (length(approved_by) between 1 and 120),
    approved_at timestamptz not null,
    expires_at timestamptz not null,
    consumed_at timestamptz,
    consumed_by text,
    created_at timestamptz not null default now(),
    check (expires_at > approved_at),
    check ((consumed_at is null) = (consumed_by is null))
);

create index if not exists papi_approval_ledger_task_idx
    on public.papi_approval_ledger(task_id, created_at desc);
create index if not exists papi_approval_ledger_expiry_idx
    on public.papi_approval_ledger(expires_at)
    where consumed_at is null;

alter table public.papi_approval_ledger enable row level security;
revoke all on public.papi_approval_ledger from public, anon, authenticated;
revoke all on public.papi_approval_ledger from service_role;
grant select on public.papi_approval_ledger to service_role;

-- Issuance is performed only by the trusted backend after authenticating the owner.
-- This database function enforces the approval's scope and maximum lifetime.
create or replace function public.papi_issue_approval(
    p_approval_id text,
    p_task_id text,
    p_handler text,
    p_action_class text,
    p_approved_by text,
    p_approved_at timestamptz,
    p_expires_at timestamptz
) returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    if p_approval_id is null or p_approval_id !~ '^[A-Za-z0-9_-]{8,120}$'
       or p_task_id is null or length(trim(p_task_id)) = 0
       or p_handler is null or length(trim(p_handler)) not between 1 and 100
       or p_action_class not in ('read_only', 'internal_write', 'external_communication', 'financial', 'legal')
       or p_approved_by is null or length(trim(p_approved_by)) not between 1 and 120
       or p_approved_at is null or p_expires_at is null
       or p_approved_at > now() + interval '60 seconds'
       or p_expires_at <= now()
       or p_expires_at <= p_approved_at
       or p_expires_at - p_approved_at > interval '15 minutes' then
        raise exception 'Invalid approval issuance request' using errcode = '22023';
    end if;

    insert into public.papi_approval_ledger(
        approval_id, task_id, handler, action_class, approved_by, approved_at, expires_at
    ) values (
        p_approval_id, p_task_id, p_handler, p_action_class,
        p_approved_by, p_approved_at, p_expires_at
    );

    insert into public.papi_audit_events(
        event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
        'approval-issued:' || p_approval_id,
        now(),
        p_approved_by,
        'approval.issued',
        'approval',
        p_approval_id,
        jsonb_build_object(
            'task_id', p_task_id,
            'handler', p_handler,
            'action_class', p_action_class,
            'expires_at', p_expires_at
        )
    );

    return true;
end;
$$;

-- A single conditional UPDATE claims the approval. Concurrent callers serialize
-- on the row; only one can change consumed_at from NULL.
-- The audit insert is in the same transaction as consumption.
create or replace function public.papi_consume_approval(
    p_approval_id text,
    p_task_id text,
    p_handler text,
    p_action_class text,
    p_consumer_id text
) returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_approved_by text;
begin
    if p_approval_id is null or p_task_id is null or p_handler is null
       or p_action_class is null or p_consumer_id is null
       or length(trim(p_consumer_id)) not between 1 and 120 then
        raise exception 'Invalid approval consumption request' using errcode = '22023';
    end if;

    update public.papi_approval_ledger
       set consumed_at = now(),
           consumed_by = p_consumer_id
     where approval_id = p_approval_id
       and task_id = p_task_id
       and handler = p_handler
       and action_class = p_action_class
       and consumed_at is null
       and expires_at > now()
    returning approved_by into v_approved_by;

    if v_approved_by is null then
        return false;
    end if;

    insert into public.papi_audit_events(
        event_id, occurred_at, actor, action, entity_type, entity_id, details
    ) values (
        'approval-consumed:' || p_approval_id,
        now(),
        p_consumer_id,
        'approval.consumed',
        'approval',
        p_approval_id,
        jsonb_build_object(
            'task_id', p_task_id,
            'handler', p_handler,
            'action_class', p_action_class,
            'approved_by', v_approved_by
        )
    );

    return true;
end;
$$;

revoke all on function public.papi_issue_approval(text, text, text, text, text, timestamptz, timestamptz)
    from public, anon, authenticated;
revoke all on function public.papi_consume_approval(text, text, text, text, text)
    from public, anon, authenticated;
grant execute on function public.papi_issue_approval(text, text, text, text, text, timestamptz, timestamptz)
    to service_role;
grant execute on function public.papi_consume_approval(text, text, text, text, text)
    to service_role;
