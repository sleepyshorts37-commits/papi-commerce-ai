-- Rollback migration 004. Refuse destructive rollback when shared data exists.
do $rollback$
begin
    if exists (select 1 from public.papi_memory_events)
       or exists (select 1 from public.papi_chat_messages) then
        raise exception 'Cannot rollback shared collaboration migration with retained data'
            using errcode = '55000';
    end if;
end;
$rollback$;

drop trigger if exists papi_memory_events_append_only on public.papi_memory_events;
drop trigger if exists papi_chat_messages_append_only on public.papi_chat_messages;
drop table if exists public.papi_memory_events;
drop table if exists public.papi_chat_messages;
drop function if exists public.papi_reject_append_only_mutation();
