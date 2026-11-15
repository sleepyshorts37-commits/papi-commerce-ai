-- Durable audit record for each private KDP package build.
create table if not exists papi_kids_private.kdp_package_builds (
    package_build_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    package_version integer not null check (package_version between 1 and 999),
    package_manifest jsonb not null check (jsonb_typeof(package_manifest) = 'object'),
    package_manifest_sha256 text not null check (package_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    build_status text not null check (build_status in ('generated_pending_manual_pdf_inspection','generated_pending_manual_multiformat_review')),
    created_at timestamptz not null default now(),
    unique (upload_id, package_version)
);

create index if not exists kdp_package_builds_latest_idx
    on papi_kids_private.kdp_package_builds(upload_id, package_version desc);

alter table papi_kids_private.kdp_package_builds enable row level security;
revoke all on papi_kids_private.kdp_package_builds from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.kdp_package_builds to service_role;
    end if;
end;
$$;
