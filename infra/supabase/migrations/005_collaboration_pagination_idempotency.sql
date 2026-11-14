-- Migration 005: stable idempotency keys and keyset-pagination indexes.
alter table public.papi_memory_events
    add column if not exists idempotency_key text;
alter table public.papi_chat_messages
    add column if not exists idempotency_key text;

do $constraints$
begin
    if not exists (select 1 from pg_constraint where conname = 'papi_memory_events_idempotency_key_unique') then
        alter table public.papi_memory_events
            add constraint papi_memory_events_idempotency_key_unique unique (idempotency_key);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'papi_chat_messages_idempotency_key_unique') then
        alter table public.papi_chat_messages
            add constraint papi_chat_messages_idempotency_key_unique unique (idempotency_key);
    end if;
end;
$constraints$;

alter table public.papi_memory_events
    add constraint papi_memory_events_idempotency_key_shape
    check (idempotency_key is null or idempotency_key ~ '^[A-Za-z0-9._:-]{8,128}$');
alter table public.papi_chat_messages
    add constraint papi_chat_messages_idempotency_key_shape
    check (idempotency_key is null or idempotency_key ~ '^[A-Za-z0-9._:-]{8,128}$');

create index if not exists papi_memory_events_shared_page_idx
    on public.papi_memory_events(created_at desc, event_id desc)
    where event_type = 'remember' and scope = 'shared';
create index if not exists papi_memory_events_agent_page_idx
    on public.papi_memory_events(actor, created_at desc, event_id desc)
    where event_type = 'remember' and scope = 'agent';
create index if not exists papi_chat_recipient_page_idx
    on public.papi_chat_messages(recipient, sent_at desc, message_id desc);
