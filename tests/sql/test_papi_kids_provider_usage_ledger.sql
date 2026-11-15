-- Disposable PostgreSQL contract test for the zero-spend provider ledger.
do $$
declare
    v_fingerprint text := repeat('e', 64);
    v_request_key text := repeat('f', 64);
    v_prompt_hash text := repeat('a', 64);
    v_reservation uuid;
begin
    if not (select relrowsecurity from pg_class where oid = 'papi_kids_private.provider_daily_usage'::regclass)
       or not (select relrowsecurity from pg_class where oid = 'papi_kids_private.provider_generation_reservations'::regclass) then
        raise exception 'RLS must be enabled on provider usage ledger';
    end if;
    if has_table_privilege('anon', 'papi_kids_private.provider_daily_usage', 'select')
       or has_table_privilege('authenticated', 'papi_kids_private.provider_daily_usage', 'select') then
        raise exception 'Client roles must not read provider usage ledger';
    end if;
    insert into papi_kids_private.provider_daily_usage(
        account_fingerprint, provider, model_id, usage_date, plan_type,
        daily_limit_neurons, evidence_ref, quota_checked_at, evidence_expires_at
    ) values (
        v_fingerprint, 'cloudflare_workers_ai', '@cf/black-forest-labs/flux-1-schnell',
        current_date, 'workers_free', 10000, 'ci-evidence', now(), now() + interval '1 hour'
    );
    update papi_kids_private.provider_daily_usage set reserved_neurons = 57.60
     where account_fingerprint = v_fingerprint and usage_date = current_date;
    insert into papi_kids_private.provider_generation_reservations(
        account_fingerprint, provider, model_id, usage_date, request_key,
        campaign_id, page_number, prompt_sha256, reserved_neurons
    ) values (
        v_fingerprint, 'cloudflare_workers_ai', '@cf/black-forest-labs/flux-1-schnell',
        current_date, v_request_key, 'CI-CAMPAIGN', 1, v_prompt_hash, 57.60
    ) returning reservation_id into v_reservation;
    update papi_kids_private.provider_daily_usage
       set reserved_neurons = reserved_neurons - 57.60,
           used_neurons = used_neurons + 57.60
     where account_fingerprint = v_fingerprint and usage_date = current_date;
    update papi_kids_private.provider_generation_reservations
       set status = 'completed', output_sha256 = repeat('b', 64), settled_at = now()
     where reservation_id = v_reservation;
    if not exists (select 1 from papi_kids_private.provider_generation_reservations
                    where reservation_id = v_reservation and status = 'completed' and cost_minor = 0) then
        raise exception 'Provider reservation did not settle at zero cost';
    end if;
end;
$$;
