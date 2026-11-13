-- Migration 20261113_001: external audit checkpoint anchor.
-- Apply only to a disposable/test database first. Safe to re-apply.
BEGIN;

-- External audit checkpoint witness. Only signed checkpoint envelopes are stored;
-- raw local audit events and business payloads are never copied here.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.papi_audit_anchor_records (
    journal_id text not null check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    record_digest text not null check (record_digest ~ '^[0-9a-f]{64}$'),
    canonical_record text not null,
    created_at timestamptz not null default now(),
    primary key (journal_id, record_digest)
);

create table if not exists public.papi_audit_anchor_heads (
    journal_id text primary key check (journal_id ~ '^[A-Za-z0-9_.:-]{1,120}$'),
    latest_record_digest text not null check (latest_record_digest ~ '^[0-9a-f]{64}$'),
    sequence bigint not null check (sequence >= 0),
    head_hash text not null check (head_hash ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz not null default now()
);

alter table public.papi_audit_anchor_records enable row level security;
alter table public.papi_audit_anchor_heads enable row level security;
revoke all on public.papi_audit_anchor_records from public, anon, authenticated;
revoke all on public.papi_audit_anchor_heads from public, anon, authenticated;
grant select, insert on public.papi_audit_anchor_records to service_role;
grant select on public.papi_audit_anchor_heads to service_role;

create or replace function public.papi_reject_audit_anchor_record_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $papi$
begin
    raise exception 'Audit anchor records are immutable' using errcode = '55000';
end;
$papi$;

drop trigger if exists papi_audit_anchor_records_immutable
    on public.papi_audit_anchor_records;
create trigger papi_audit_anchor_records_immutable
    before update or delete on public.papi_audit_anchor_records
    for each row execute function public.papi_reject_audit_anchor_record_mutation();

-- SECURITY DEFINER: keep pg_catalog first, qualify the extension digest function,
-- and never rely on an untrusted schema shadowing built-ins or helper functions.
create or replace function public.papi_advance_audit_anchor(
    p_journal_id text,
    p_expected_digest text,
    p_new_digest text
) returns boolean
language plpgsql
security definer
set search_path = pg_catalog, public, extensions, pg_temp
as $papi$
declare
    v_canonical text;
    v_record jsonb;
    v_checkpoint jsonb;
    v_sequence bigint;
    v_head_hash text;
    v_previous_digest text;
    v_key_id text;
    v_signature text;
    v_current public.papi_audit_anchor_heads%rowtype;
begin
    if p_journal_id is null or pg_catalog.length(p_journal_id) not between 1 and 120
       or p_journal_id ~ '[^A-Za-z0-9_.:-]'
       or p_new_digest is null or pg_catalog.length(p_new_digest) <> 64
       or p_new_digest ~ '[^0-9a-f]'
       or (p_expected_digest is not null and (
           pg_catalog.length(p_expected_digest) <> 64
           or p_expected_digest ~ '[^0-9a-f]'
       )) then
        raise exception 'Invalid audit anchor pointer' using errcode = '22023';
    end if;

    select canonical_record into v_canonical
      from public.papi_audit_anchor_records
     where journal_id = p_journal_id and record_digest = p_new_digest;
    if not found then
        raise exception 'Audit anchor record not found' using errcode = '22023';
    end if;
    if pg_catalog.encode(
        extensions.digest(pg_catalog.convert_to(v_canonical, 'UTF8'), 'sha256'),
        'hex'
    ) <> p_new_digest then
        raise exception 'Audit anchor record digest mismatch' using errcode = '22023';
    end if;

    begin
        v_record := v_canonical::jsonb;
        if pg_catalog.jsonb_typeof(v_record) <> 'object' then
            raise exception 'record must be an object';
        end if;
        if not (v_record ?& array['schema_version', 'journal_id', 'checkpoint', 'previous_record_digest', 'key_id', 'signature']) then
            raise exception 'record is missing required fields';
        end if;
        if (v_record - array[
            'schema_version', 'journal_id', 'checkpoint',
            'previous_record_digest', 'key_id', 'signature'
        ]) <> '{}'::jsonb then
            raise exception 'record contains unknown fields';
        end if;
        if pg_catalog.jsonb_typeof(v_record->'schema_version') <> 'number'
           or (v_record->>'schema_version')::integer <> 1 then
            raise exception 'unsupported record schema';
        end if;
        if v_record->>'journal_id' is distinct from p_journal_id then
            raise exception 'journal mismatch';
        end if;

        v_checkpoint := v_record->'checkpoint';
        if pg_catalog.jsonb_typeof(v_checkpoint) <> 'object'
           or not (v_checkpoint ?& array['schema_version', 'sequence', 'head_hash'])
           or (v_checkpoint - array['schema_version', 'sequence', 'head_hash']) <> '{}'::jsonb
           or pg_catalog.jsonb_typeof(v_checkpoint->'schema_version') <> 'number'
           or (v_checkpoint->>'schema_version')::integer <> 1
           or pg_catalog.jsonb_typeof(v_checkpoint->'sequence') <> 'number'
           or (v_checkpoint->>'sequence')::numeric < 0
           or (v_checkpoint->>'sequence')::numeric <> pg_catalog.trunc((v_checkpoint->>'sequence')::numeric)
 then
            raise exception 'invalid checkpoint envelope';
        end if;
        v_sequence := (v_checkpoint->>'sequence')::bigint;
        v_head_hash := v_checkpoint->>'head_hash';
        v_previous_digest := v_record->>'previous_record_digest';
        v_key_id := v_record->>'key_id';
        v_signature := v_record->>'signature';
    exception when others then
        raise exception 'Malformed audit anchor record' using errcode = '22023';
    end;

    if v_sequence < 0
       or v_head_hash is null or pg_catalog.length(v_head_hash) <> 64 or v_head_hash ~ '[^0-9a-f]'
       or (v_previous_digest is not null and (pg_catalog.length(v_previous_digest) <> 64 or v_previous_digest ~ '[^0-9a-f]'))
       or v_previous_digest is distinct from p_expected_digest
       or v_key_id is null or pg_catalog.length(v_key_id) not between 1 and 120 or v_key_id ~ '[^A-Za-z0-9_.:-]'

       or v_signature is null or pg_catalog.length(v_signature) = 0
       or pg_catalog.length(v_signature) > 2048 then
        raise exception 'Audit anchor record fields do not match pointer' using errcode = '22023';
    end if;

    -- Genesis insert; ON CONFLICT handles two concurrent first publishers.
    if p_expected_digest is null then
        insert into public.papi_audit_anchor_heads(
            journal_id, latest_record_digest, sequence, head_hash
        ) values (p_journal_id, p_new_digest, v_sequence, v_head_hash)
        on conflict (journal_id) do nothing;
        if found then
            return true;
        end if;
    end if;

    select * into v_current
      from public.papi_audit_anchor_heads
     where journal_id = p_journal_id
     for update;

    if not found then
        return false;
    end if;
    if v_current.latest_record_digest = p_new_digest then
        return v_current.sequence = v_sequence and v_current.head_hash = v_head_hash;
    end if;
    if v_current.latest_record_digest is distinct from p_expected_digest then
        return false;
    end if;
    if v_sequence <= v_current.sequence then
        raise exception 'Audit anchor sequence must increase' using errcode = '22023';
    end if;

    update public.papi_audit_anchor_heads
       set latest_record_digest = p_new_digest,
           sequence = v_sequence,
           head_hash = v_head_hash,
           updated_at = pg_catalog.now()
     where journal_id = p_journal_id;
    return true;
end;
$papi$;

revoke all on function public.papi_reject_audit_anchor_record_mutation() from public, anon, authenticated;
revoke all on function public.papi_advance_audit_anchor(text, text, text) from public, anon, authenticated;
grant execute on function public.papi_advance_audit_anchor(text, text, text) to service_role;

COMMIT;
