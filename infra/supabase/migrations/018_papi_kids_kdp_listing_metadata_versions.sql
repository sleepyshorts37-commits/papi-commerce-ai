-- Append-only versions of the owner-entered Amazon KDP listing metadata.
create table if not exists papi_kids_private.kdp_listing_metadata_versions (
    metadata_version_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    version integer not null check (version > 0),
    metadata_json jsonb not null check (jsonb_typeof(metadata_json) = 'object'),
    metadata_sha256 text not null check (metadata_sha256 ~ '^[0-9a-f]{64}$'),
    validation_status text not null check (validation_status in ('incomplete','ready_for_owner_review')),
    blocker_count integer not null check (blocker_count between 0 and 100),
    updated_by text not null check (length(updated_by) between 3 and 120),
    created_at timestamptz not null default now(),
    unique (upload_id, version)
);

create index if not exists kdp_listing_metadata_versions_latest_idx
    on papi_kids_private.kdp_listing_metadata_versions(upload_id, version desc);

alter table papi_kids_private.kdp_listing_metadata_versions enable row level security;
revoke all on papi_kids_private.kdp_listing_metadata_versions from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.kdp_listing_metadata_versions to service_role;
    end if;
end;
$$;
