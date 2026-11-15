-- PAPI KIDS durable editorial queue. Apply only through a reviewed deployment migration.
create schema if not exists papi_kids_private;
revoke all on schema papi_kids_private from public;

create table if not exists papi_kids_private.books (
    book_id uuid primary key default gen_random_uuid(),
    upload_id text not null unique,
    source_sha256 text not null unique check (source_sha256 ~ '^[0-9a-f]{64}$'),
    original_filename text not null,
    title text,
    status text not null default 'received'
        check (status in ('received','queued_for_analysis','analysis_ready','needs_editor_review','failed')),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists papi_kids_private.editorial_jobs (
    job_id bigint generated always as identity primary key,
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    job_type text not null check (job_type in ('editorial_structure_analysis')),
    status text not null default 'queued'
        check (status in ('queued','processing','completed','failed')),
    payload jsonb not null default '{}'::jsonb,
    attempts integer not null default 0 check (attempts >= 0),
    max_attempts integer not null default 5 check (max_attempts between 1 and 20),
    available_at timestamptz not null default now(),
    lease_owner text,
    lease_until timestamptz,
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (book_id, job_type),
    check ((status = 'processing') = (lease_owner is not null and lease_until is not null))
);

create index if not exists editorial_jobs_ready_idx
    on papi_kids_private.editorial_jobs (available_at, created_at)
    where status = 'queued';
create index if not exists editorial_jobs_expired_lease_idx
    on papi_kids_private.editorial_jobs (lease_until)
    where status = 'processing';

create table if not exists papi_kids_private.editorial_job_events (
    event_id bigint generated always as identity primary key,
    job_id bigint not null references papi_kids_private.editorial_jobs(job_id) on delete cascade,
    event_type text not null,
    worker_id text,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

alter table papi_kids_private.books enable row level security;
alter table papi_kids_private.editorial_jobs enable row level security;
alter table papi_kids_private.editorial_job_events enable row level security;
revoke all on all tables in schema papi_kids_private from public;

create or replace function papi_kids_private.claim_editorial_job(
    p_worker_id text,
    p_lease_seconds integer default 300
)
returns setof papi_kids_private.editorial_jobs
language plpgsql
security invoker
set search_path = pg_catalog, papi_kids_private
as $$
begin
    if p_worker_id is null or length(trim(p_worker_id)) < 3 or length(p_worker_id) > 120 then
        raise exception 'invalid worker id';
    end if;
    return query
    with candidate as (
        select job_id
        from papi_kids_private.editorial_jobs
        where (
            (status = 'queued' and available_at <= now())
            or (status = 'processing' and lease_until < now())
        )
        and attempts < max_attempts
        order by available_at, created_at
        for update skip locked
        limit 1
    )
    update papi_kids_private.editorial_jobs j
       set status = 'processing',
           attempts = j.attempts + 1,
           lease_owner = p_worker_id,
           lease_until = now() + make_interval(secs => greatest(30, least(coalesce(p_lease_seconds, 300), 3600))),
           updated_at = now()
      from candidate c
     where j.job_id = c.job_id
    returning j.*;
end;
$$;

revoke all on function papi_kids_private.claim_editorial_job(text, integer) from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant usage on schema papi_kids_private to service_role;
        grant select, insert, update on papi_kids_private.books to service_role;
        grant select, insert, update on papi_kids_private.editorial_jobs to service_role;
        grant select, insert on papi_kids_private.editorial_job_events to service_role;
        grant usage, select on all sequences in schema papi_kids_private to service_role;
        grant execute on function papi_kids_private.claim_editorial_job(text, integer) to service_role;
    end if;
end;
$$;
