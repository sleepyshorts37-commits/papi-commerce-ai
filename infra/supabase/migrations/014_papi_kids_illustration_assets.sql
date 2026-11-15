-- Private PAPI KIDS illustration asset registry and visual review audit.
create table if not exists papi_kids_private.illustration_assets (
    asset_id text primary key check (asset_id ~ '^PKP-ASSET-[0-9a-f]{24}$'),
    book_id uuid not null references papi_kids_private.books(book_id) on delete cascade,
    page_number integer not null check (page_number between 1 and 200),
    version integer not null check (version between 1 and 1000),
    source_sha256 text not null unique check (source_sha256 ~ '^[0-9a-f]{64}$'),
    storage_key text not null unique,
    media_type text not null check (media_type in ('image/png','image/jpeg','image/webp')),
    width_px integer not null check (width_px > 0 and width_px <= 12000),
    height_px integer not null check (height_px > 0 and height_px <= 12000),
    review_status text not null default 'pending_review'
        check (review_status in ('pending_review','approved','rejected','superseded')),
    source_provider text,
    model_id text,
    prompt_sha256 text check (prompt_sha256 is null or prompt_sha256 ~ '^[0-9a-f]{64}$'),
    generation_ref text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    reviewed_by text,
    unique (book_id, page_number, version)
);

create index if not exists illustration_assets_book_page_idx
    on papi_kids_private.illustration_assets (book_id, page_number, version desc);

create table if not exists papi_kids_private.illustration_review_events (
    event_id bigint generated always as identity primary key,
    asset_id text not null references papi_kids_private.illustration_assets(asset_id) on delete cascade,
    event_type text not null check (event_type in ('uploaded','approved','rejected','superseded','reopened')),
    actor text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

alter table papi_kids_private.illustration_assets enable row level security;
alter table papi_kids_private.illustration_review_events enable row level security;
revoke all on all tables in schema papi_kids_private from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert, update on papi_kids_private.illustration_assets to service_role;
        grant select, insert on papi_kids_private.illustration_review_events to service_role;
        grant usage, select on all sequences in schema papi_kids_private to service_role;
    end if;
end;
$$;
