-- PAPI COMMERCE AI — migration 004
-- Persistance partagée append-only pour mémoire et messagerie interne.
-- À appliquer après schema.sql dans un environnement de test contrôlé.
-- Le filtrage par identité/portée reste obligatoire dans l'adaptateur applicatif.

create table if not exists public.papi_memory_events (
    event_id uuid primary key,
    memory_id uuid not null,
    event_type text not null check (event_type in ('remember', 'supersede')),
    created_at timestamptz not null,
    actor text not null check (actor ~ '^[A-Za-z0-9_-]{1,100}$'),
    category text,
    title text,
    content text,
    source_type text,
    source_id text,
    confidence numeric(4,3),
    scope text,
    tags text[] not null default '{}',
    sensitivity text,
    target_memory_id uuid,
    reason text,
    constraint papi_memory_event_shape check (
        (event_type = 'remember'
         and category in ('fact', 'project', 'result', 'procedure', 'lesson')
         and title is not null and length(title) between 1 and 120
         and content is not null and length(content) between 1 and 2000
         and source_type is not null and length(source_type) between 1 and 40
         and source_id is not null and length(source_id) between 1 and 120
         and confidence between 0 and 1
         and scope in ('shared', 'agent')
         and cardinality(tags) <= 10
         and sensitivity = 'normal'
         and target_memory_id is null and reason is null)
        or
        (event_type = 'supersede'
         and target_memory_id is not null
         and reason is not null and length(reason) between 1 and 240
         and category is null and title is null and content is null
         and source_type is null and source_id is null
         and confidence is null and scope is null
         and cardinality(tags) = 0 and sensitivity is null)
    )
);

create index if not exists papi_memory_events_memory_idx
    on public.papi_memory_events(memory_id, created_at);
create index if not exists papi_memory_events_actor_scope_idx
    on public.papi_memory_events(actor, scope, created_at);

create table if not exists public.papi_chat_messages (
    message_id text primary key check (message_id ~ '^MSG-[A-F0-9]{32}$'),
    sent_at timestamptz not null,
    sender text not null check (sender ~ '^[A-Za-z0-9_-]{1,100}$'),
    recipient text not null check (recipient = 'all' or recipient ~ '^[A-Za-z0-9_-]{1,100}$'),
    subject text not null check (length(subject) between 1 and 120),
    body text not null check (length(body) between 1 and 2000),
    message_type text not null check (message_type in ('info', 'task', 'alert', 'report'))
);

create index if not exists papi_chat_recipient_sent_idx
    on public.papi_chat_messages(recipient, sent_at, message_id);
create index if not exists papi_chat_sent_idx
    on public.papi_chat_messages(sent_at, message_id);

-- Append-only guard: updates and deletes are denied even to the server role.
create or replace function public.papi_reject_append_only_mutation()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public, pg_temp
as $append_only$
begin
    raise exception 'Append-only records cannot be changed' using errcode = '55000';
end;
$append_only$;

drop trigger if exists papi_memory_events_append_only on public.papi_memory_events;
create trigger papi_memory_events_append_only
    before update or delete on public.papi_memory_events
    for each row execute function public.papi_reject_append_only_mutation();

drop trigger if exists papi_chat_messages_append_only on public.papi_chat_messages;
create trigger papi_chat_messages_append_only
    before update or delete on public.papi_chat_messages
    for each row execute function public.papi_reject_append_only_mutation();

alter table public.papi_memory_events enable row level security;
alter table public.papi_chat_messages enable row level security;
revoke all on public.papi_memory_events from public, anon, authenticated;
revoke all on public.papi_chat_messages from public, anon, authenticated;
grant select, insert on public.papi_memory_events to service_role;
grant select, insert on public.papi_chat_messages to service_role;
revoke all on function public.papi_reject_append_only_mutation() from public, anon, authenticated;
