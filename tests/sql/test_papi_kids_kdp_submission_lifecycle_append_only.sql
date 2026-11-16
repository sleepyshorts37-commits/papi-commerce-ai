begin;

do $$
declare
    book uuid;
    event_id uuid;
    upload_ref text := 'PKP-UP-' || replace(gen_random_uuid()::text, '-', '');
    delete_rule "char";
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'papi_kids_private.kdp_submission_lifecycle_events'::regclass
           and tgname = 'kdp_submission_lifecycle_events_append_only'
           and not tgisinternal
           and tgenabled <> 'D'
    ) then
        raise exception 'Lifecycle append-only trigger is missing or disabled';
    end if;

    select confdeltype into delete_rule
      from pg_constraint
     where conrelid = 'papi_kids_private.kdp_submission_lifecycle_events'::regclass
       and confrelid = 'papi_kids_private.books'::regclass
       and contype = 'f';
    if delete_rule is distinct from 'r' then
        raise exception 'Lifecycle book foreign key must use ON DELETE RESTRICT';
    end if;

    insert into papi_kids_private.books
        (upload_id, source_sha256, original_filename, status, metadata)
    values
        (upload_ref, repeat('a', 64), 'ci-kdp-lifecycle.txt', 'received', '{}'::jsonb)
    returning book_id into book;

    insert into papi_kids_private.kdp_submission_lifecycle_events
        (book_id, upload_id, package_version, manifest_sha256, status,
         owner_id, evidence_sha256, notes)
    values
        (book, upload_ref, 1, repeat('b', 64), 'submitted_manual',
         'ci-owner', repeat('c', 64), 'Disposable database append-only contract test.')
    returning lifecycle_event_id into event_id;

    begin
        update papi_kids_private.kdp_submission_lifecycle_events
           set notes = 'Attempted mutation of an audit event.'
         where lifecycle_event_id = event_id;
        raise exception 'Lifecycle UPDATE unexpectedly succeeded';
    exception when sqlstate '55000' then
        null;
    end;

    begin
        delete from papi_kids_private.kdp_submission_lifecycle_events
         where lifecycle_event_id = event_id;
        raise exception 'Lifecycle DELETE unexpectedly succeeded';
    exception when sqlstate '55000' then
        null;
    end;

    begin
        delete from papi_kids_private.books where book_id = book;
        raise exception 'Parent book deletion unexpectedly erased lifecycle evidence';
    exception when foreign_key_violation then
        null;
    end;

    if not exists (
        select 1 from papi_kids_private.kdp_submission_lifecycle_events
         where lifecycle_event_id = event_id
    ) or not exists (
        select 1 from papi_kids_private.books where book_id = book
    ) then
        raise exception 'Lifecycle evidence or parent book was not preserved';
    end if;
end;
$$;

rollback;
