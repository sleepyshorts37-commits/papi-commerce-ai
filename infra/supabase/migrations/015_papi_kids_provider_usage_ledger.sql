-- Shared, transactional daily neuron ledger and per-image generation reservations.
create table if not exists papi_kids_private.provider_daily_usage (
    account_fingerprint text not null check (account_fingerprint ~ '^[0-9a-f]{64}$'),
    provider text not null check (provider = 'cloudflare_workers_ai'),
    model_id text not null check (model_id = '@cf/black-forest-labs/flux-1-schnell'),
    usage_date date not null,
    plan_type text not null check (plan_type = 'workers_free'),
    daily_limit_neurons numeric(14,2) not null check (daily_limit_neurons = 10000),
    used_neurons numeric(14,2) not null default 0 check (used_neurons >= 0),
    reserved_neurons numeric(14,2) not null default 0 check (reserved_neurons >= 0),
    evidence_ref text not null,
    quota_checked_at timestamptz not null,
    evidence_expires_at timestamptz not null,
    updated_at timestamptz not null default now(),
    primary key (account_fingerprint, provider, model_id, usage_date),
    check (used_neurons + reserved_neurons <= daily_limit_neurons)
);
create table if not exists papi_kids_private.provider_generation_reservations (
    reservation_id uuid primary key default gen_random_uuid(),
    account_fingerprint text not null,
    provider text not null,
    model_id text not null,
    usage_date date not null,
    request_key text not null unique check (request_key ~ '^[0-9a-f]{64}$'),
    campaign_id text not null,
    page_number integer not null check (page_number between 1 and 200),
    prompt_sha256 text not null check (prompt_sha256 ~ '^[0-9a-f]{64}$'),
    reserved_neurons numeric(14,2) not null check (reserved_neurons > 0),
    status text not null default 'reserved'
        check (status in ('reserved','completed','released','failed_consumed')),
    cost_minor integer not null default 0 check (cost_minor = 0),
    output_sha256 text check (output_sha256 is null or output_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    settled_at timestamptz,
    foreign key (account_fingerprint, provider, model_id, usage_date)
        references papi_kids_private.provider_daily_usage(
            account_fingerprint, provider, model_id, usage_date
        )
);
create index if not exists provider_reservations_status_idx
    on papi_kids_private.provider_generation_reservations(status, created_at);
alter table papi_kids_private.provider_daily_usage enable row level security;
alter table papi_kids_private.provider_generation_reservations enable row level security;
revoke all on all tables in schema papi_kids_private from public;
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant select, insert, update on papi_kids_private.provider_daily_usage to service_role;
        grant select, insert, update on papi_kids_private.provider_generation_reservations to service_role;
    end if;
end;
$$;
