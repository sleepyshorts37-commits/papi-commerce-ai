-- Destructive rollback is intentionally refused when approval history exists.
begin;
do $guard$
begin
  if exists (select 1 from public.papi_approval_ledger) then
    raise exception 'Refusing approval-ledger rollback: approval records exist';
  end if;
  if exists (
    select 1 from public.papi_audit_events
    where action in ('approval.issued', 'approval.consumed')
  ) then
    raise exception 'Refusing approval-ledger rollback: audit history exists';
  end if;
end
$guard$;
drop function if exists public.papi_consume_approval(text, text, text, text, text);
drop function if exists public.papi_issue_approval(text, text, text, text, text, timestamptz, timestamptz);
drop table if exists public.papi_approval_ledger;
commit;
