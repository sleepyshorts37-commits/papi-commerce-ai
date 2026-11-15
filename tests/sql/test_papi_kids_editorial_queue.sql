-- Disposable PostgreSQL contract test for the private PAPI KIDS queue.
do $$
declare
    v_book uuid;
    v_job bigint;
    v_claimed papi_kids_private.editorial_jobs%rowtype;
begin
    if not (select relrowsecurity from pg_class where oid = 'papi_kids_private.books'::regclass)
       or not (select relrowsecurity from pg_class where oid = 'papi_kids_private.editorial_jobs'::regclass)
       or not (select relrowsecurity from pg_class where oid = 'papi_kids_private.editorial_job_events'::regclass) then
        raise exception 'RLS must be enabled on every private queue table';
    end if;
    if has_schema_privilege('anon', 'papi_kids_private', 'usage')
       or has_schema_privilege('authenticated', 'papi_kids_private', 'usage') then
        raise exception 'Client roles must not access the private queue schema';
    end if;
    if not has_schema_privilege('service_role', 'papi_kids_private', 'usage') then
        raise exception 'service_role must have private schema usage';
    end if;

    insert into papi_kids_private.books(upload_id, source_sha256, original_filename)
    values ('PKP-UP-' || repeat('a', 32), repeat('b', 64), 'nia.md')
    returning book_id into v_book;

    insert into papi_kids_private.editorial_jobs(book_id, job_type, payload)
    values (v_book, 'editorial_structure_analysis', jsonb_build_object('ai_invoked', false))
    returning job_id into v_job;

    select * into v_claimed
      from papi_kids_private.claim_editorial_job('ci-worker-001', 90);
    if v_claimed.job_id <> v_job
       or v_claimed.status <> 'processing'
       or v_claimed.lease_owner <> 'ci-worker-001'
       or v_claimed.attempts <> 1
       or v_claimed.lease_until <= now() then
        raise exception 'Atomic claim did not assign a valid lease';
    end if;

    update papi_kids_private.editorial_jobs
       set status = 'completed', lease_owner = null, lease_until = null
     where job_id = v_job and lease_owner = 'ci-worker-001';
    if not found then
        raise exception 'Leased job could not be completed by its owner';
    end if;
end;
$$;
