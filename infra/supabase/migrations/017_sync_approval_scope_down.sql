-- Rollback only when no sync-approval records or audit history exist.
begin;
do $guard$
begin
  if exists (select 1 from public.papi_approval_ledger where scope_digest is not null)
     or exists (select 1 from public.papi_audit_events
                where action in ('sync_approval.issued','sync_approval.consumed')) then
    raise exception 'Refusing sync approval rollback: approval history exists';
  end if;
end
$guard$;
drop function if exists public.papi_consume_sync_approval(text,text,text,text,text,text,jsonb);
drop function if exists public.papi_issue_sync_approval(text,text,text,text,text,timestamptz,timestamptz,text,text,jsonb);
alter table public.papi_approval_ledger drop constraint if exists papi_approval_sync_scope_check;
alter table public.papi_approval_ledger
  drop column if exists scope_digest,
  drop column if exists destination_instance,
  drop column if exists action_ids;
commit;
