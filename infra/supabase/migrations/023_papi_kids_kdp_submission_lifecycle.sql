-- Append-only manual Amazon KDP submission and publication lifecycle evidence.
create table if not exists papi_kids_private.kdp_submission_lifecycle_events (
    lifecycle_event_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    package_version integer not null check (package_version between 1 and 999),
    manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    status text not null check (status in (
        'submitted_manual', 'proof_received', 'proof_approved',
        'live_verified_by_owner', 'rejected', 'action_required'
    )),
    asin text check (asin is null or asin ~ '^[A-Z0-9]{10}$'),
    listing_url text,
    owner_id text not null check (length(owner_id) between 3 and 120),
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    notes text not null check (length(notes) between 20 and 2000),
    recorded_at timestamptz not null default now()
);

create index if not exists kdp_submission_lifecycle_latest_idx
    on papi_kids_private.kdp_submission_lifecycle_events(upload_id, recorded_at desc);

alter table papi_kids_private.kdp_submission_lifecycle_events enable row level security;
revoke all on papi_kids_private.kdp_submission_lifecycle_events from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.kdp_submission_lifecycle_events to service_role;
    end if;
end;
$$;
