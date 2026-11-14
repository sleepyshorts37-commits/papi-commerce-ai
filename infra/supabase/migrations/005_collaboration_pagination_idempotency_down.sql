-- Rollback migration 005 without dropping collaboration records.
alter table public.papi_memory_events
    drop constraint if exists papi_memory_events_idempotency_key_shape;
alter table public.papi_chat_messages
    drop constraint if exists papi_chat_messages_idempotency_key_shape;

do $rollback$
begin
    if exists (select 1 from public.papi_memory_events where idempotency_key is not null)
       or exists (select 1 from public.papi_chat_messages where idempotency_key is not null) then
        raise exception 'Cannot rollback idempotency columns while keys are in use'
            using errcode = '55000';
    end if;
end;
$rollback$;

alter table public.papi_memory_events
    drop constraint if exists papi_memory_events_idempotency_key_unique,
    drop column if exists idempotency_key;
alter table public.papi_chat_messages
    drop constraint if exists papi_chat_messages_idempotency_key_unique,
    drop column if exists idempotency_key;
drop index if exists public.papi_memory_events_shared_page_idx;
drop index if exists public.papi_memory_events_agent_page_idx;
drop index if exists public.papi_chat_recipient_page_idx;
