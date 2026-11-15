-- Disposable PostgreSQL contract test for illustration asset registry.
do $$
declare
    v_book uuid;
    v_asset text := 'PKP-ASSET-' || repeat('c', 24);
begin
    if not (select relrowsecurity from pg_class where oid = 'papi_kids_private.illustration_assets'::regclass)
       or not (select relrowsecurity from pg_class where oid = 'papi_kids_private.illustration_review_events'::regclass) then
        raise exception 'RLS must be enabled for illustration asset records and audit';
    end if;
    if has_table_privilege('anon', 'papi_kids_private.illustration_assets', 'select')
       or has_table_privilege('authenticated', 'papi_kids_private.illustration_assets', 'select') then
        raise exception 'Client roles must not read private illustration assets';
    end if;
    select book_id into v_book from papi_kids_private.books
     where upload_id = 'PKP-UP-' || repeat('a', 32);
    if v_book is null then
        raise exception 'Prerequisite book row is missing';
    end if;
    insert into papi_kids_private.illustration_assets(
        asset_id, book_id, page_number, version, source_sha256, storage_key,
        media_type, width_px, height_px, metadata
    ) values (
        v_asset, v_book, 1, 1, repeat('d', 64), 'private/PKP-0001/page-01-v001.png',
        'image/png', 2550, 2550, '{"qa_status":"pending_review"}'::jsonb
    );
    insert into papi_kids_private.illustration_review_events(asset_id, event_type, actor)
    values (v_asset, 'uploaded', 'ci-test');
    if not exists (select 1 from papi_kids_private.illustration_review_events
                    where asset_id = v_asset and event_type = 'uploaded') then
        raise exception 'Asset audit event was not persisted';
    end if;
end;
$$;
