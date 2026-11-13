-- PAPI COMMERCE AI — enforce active Ed25519 key version during nonce consumption.
-- This migration supersedes the legacy three-argument RPC from the initial schema.

do $
begin
    if to_regprocedure('public.papi_consume_agent_nonce(text,text,timestamp with time zone)') is not null then
        execute 'revoke all on function public.papi_consume_agent_nonce(text, text, timestamptz) from public, anon, authenticated, service_role';
        execute 'drop function public.papi_consume_agent_nonce(text, text, timestamptz)';
    end if;
end;
$;

create or replace function public.papi_consume_agent_nonce(
    p_agent_id text,
    p_key_version integer,
    p_nonce text,
    p_expires_at timestamptz
) returns boolean
language plpgsql
security invoker
set search_path = pg_catalog, public, pg_temp
as $$
declare
    v_inserted integer;
begin
    if p_agent_id is null or p_agent_id !~ '^[A-Za-z0-9_-]{1,100}$'
       or p_key_version is null or p_key_version < 1
       or p_nonce is null or length(p_nonce) < 16 or length(p_nonce) > 128
       or p_expires_at is null or p_expires_at <= now()
       or p_expires_at > now() + interval '10 minutes' then
        raise exception 'Invalid agent nonce' using errcode = '22023';
    end if;

    -- Keep the active key row locked until this transaction commits.
    -- A concurrent rotation/revocation must wait; an already revoked key is denied.
    perform 1
      from public.papi_agent_public_keys
     where agent_id = p_agent_id
       and key_version = p_key_version
       and status = 'active'
     for share;

    if not found then
        return false;
    end if;

    delete from public.papi_agent_used_nonces where expires_at < now();

    insert into public.papi_agent_used_nonces(agent_id, nonce, expires_at)
    values (p_agent_id, p_nonce, p_expires_at)
    on conflict (agent_id, nonce) do nothing;

    get diagnostics v_inserted = row_count;
    return v_inserted = 1;
end;
$$;

revoke all on function public.papi_consume_agent_nonce(text, integer, text, timestamptz)
    from public, anon, authenticated;
grant execute on function public.papi_consume_agent_nonce(text, integer, text, timestamptz)
    to service_role;
