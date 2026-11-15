-- Explicit owner sign-off for the exact, fully reviewed KDP package.
create table if not exists papi_kids_private.kdp_owner_release_authorizations (
    authorization_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    package_version integer not null check (package_version between 1 and 999),
    manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    owner_id text not null check (length(owner_id) between 3 and 120),
    confirmation_phrase text not null check (confirmation_phrase = 'I AUTHORIZE MANUAL KDP SUBMISSION'),
    confirmed_at timestamptz not null default now(),
    notes text not null check (length(notes) between 20 and 2000),
    evidence_ref text not null unique check (evidence_ref ~ '^[0-9a-f]{64}$'),
    unique (upload_id, package_version, manifest_sha256)
);

create index if not exists kdp_owner_release_authorizations_latest_idx
    on papi_kids_private.kdp_owner_release_authorizations(upload_id, package_version, confirmed_at desc);

alter table papi_kids_private.kdp_owner_release_authorizations enable row level security;
revoke all on papi_kids_private.kdp_owner_release_authorizations from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.kdp_owner_release_authorizations to service_role;
    end if;
end;
$$;
