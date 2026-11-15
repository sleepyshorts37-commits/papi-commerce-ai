-- Durable human review of child-safety screening, bound to the exact manuscript hash.
create table if not exists papi_kids_private.manuscript_safety_reviews (
    review_id uuid primary key default gen_random_uuid(),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    upload_id text not null check (upload_id ~ '^PKP-UP-[0-9a-f]{32}$'),
    manuscript_sha256 text not null check (manuscript_sha256 ~ '^[0-9a-f]{64}$'),
    decision text not null check (decision in ('approved','rejected')),
    reviewer_id text not null check (length(reviewer_id) between 3 and 120),
    reviewed_at timestamptz not null default now(),
    evidence_ref text not null unique check (evidence_ref ~ '^[0-9a-f]{64}$'),
    resolution_notes text not null default '',
    issue_count_reviewed integer not null default 0 check (issue_count_reviewed between 0 and 1000),
    critical_issue_count_reviewed integer not null default 0 check (
        critical_issue_count_reviewed between 0 and issue_count_reviewed
    )
);

create index if not exists manuscript_safety_reviews_latest_idx
    on papi_kids_private.manuscript_safety_reviews(upload_id, manuscript_sha256, reviewed_at desc);

alter table papi_kids_private.manuscript_safety_reviews enable row level security;
revoke all on papi_kids_private.manuscript_safety_reviews from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert on papi_kids_private.manuscript_safety_reviews to service_role;
    end if;
end;
$$;
