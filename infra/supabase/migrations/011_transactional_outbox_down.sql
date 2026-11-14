-- Mission 27 rollback refuses to erase delivery and attempt history.
begin;
do $guard$
begin
  if exists (select 1 from public.papi_outbox)
     or exists (select 1 from public.papi_outbox_attempts) then
    raise exception 'Refusing outbox rollback: event or attempt history exists';
  end if;
end
$guard$;
drop function if exists public.papi_outbox_health();
drop function if exists public.papi_finish_outbox(uuid, text, uuid, boolean, text);
drop function if exists public.papi_claim_outbox(text, uuid, integer);
drop function if exists public.papi_enqueue_outbox(text, text, text, jsonb, integer);
drop table if exists public.papi_outbox_attempts;
drop table if exists public.papi_outbox;
commit;
