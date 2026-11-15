-- Human Kindle Previewer attestation bound to the exact EPUB package hash.
create table if not exists papi_kids_private.kindle_previewer_reviews (
    preview_review_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    package_version integer not null check (package_version between 1 and 999),
    epub_sha256 text not null check (epub_sha256 ~ '^[0-9a-f]{64}$'),
    passed boolean not null,
    reviewer_id text not null check (length(reviewer_id) between 3 and 120),
    reviewed_at timestamptz not null default now(),
    evidence_ref text not null check (evidence_ref ~ '^[0-9a-f]{64}$'),
    notes text not null check (length(notes) between 20 and 2000)
);

create index if not exists kindle_previewer_reviews_latest_idx
    on papi_kids_private.kindle_previewer_reviews(upload_id, package_version, reviewed_at desc);

alter table papi_kids_private.kindle_previewer_reviews enable row level security;
revoke all on papi_kids_private.kindle_previewer_reviews from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.kindle_previewer_reviews to service_role;
    end if;
end;
$$;
