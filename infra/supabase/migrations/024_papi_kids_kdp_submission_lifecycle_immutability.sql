-- Preserve the KDP submission lifecycle as a genuinely append-only audit trail.
-- Book deletion must not erase submission evidence.
alter table papi_kids_private.kdp_submission_lifecycle_events
    drop constraint if exists kdp_submission_lifecycle_events_book_id_fkey;

alter table papi_kids_private.kdp_submission_lifecycle_events
    add constraint kdp_submission_lifecycle_events_book_id_fkey
    foreign key (book_id)
    references papi_kids_private.books(book_id)
    on delete restrict;

create or replace function papi_kids_private.reject_kdp_submission_lifecycle_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog, papi_kids_private
as $$
begin
    raise exception 'KDP submission lifecycle events are append-only'
        using errcode = '55000';
end;
$$;

revoke all on function papi_kids_private.reject_kdp_submission_lifecycle_mutation() from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        grant execute on function papi_kids_private.reject_kdp_submission_lifecycle_mutation() to service_role;
        revoke update, delete on papi_kids_private.kdp_submission_lifecycle_events from service_role;
    end if;
end;
$$;

drop trigger if exists kdp_submission_lifecycle_events_append_only
    on papi_kids_private.kdp_submission_lifecycle_events;

create trigger kdp_submission_lifecycle_events_append_only
    before update or delete on papi_kids_private.kdp_submission_lifecycle_events
    for each row execute function papi_kids_private.reject_kdp_submission_lifecycle_mutation();
