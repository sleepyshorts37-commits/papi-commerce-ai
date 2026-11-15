-- Disposable SQL contract for image source-resolution provenance.
do $$
declare
    v_asset papi_kids_private.illustration_assets%rowtype;
begin
    select * into v_asset
      from papi_kids_private.illustration_assets
     where asset_id = 'PKP-ASSET-' || repeat('c', 24);
    if v_asset.asset_id is null then
        raise exception 'Illustration asset fixture missing';
    end if;
    if v_asset.source_width_px <> v_asset.width_px
       or v_asset.source_height_px <> v_asset.height_px
       or v_asset.upscaling_method <> 'native' then
        raise exception 'Existing assets were not backfilled with source dimensions';
    end if;
    if not (select relrowsecurity from pg_class
             where oid = 'papi_kids_private.illustration_assets'::regclass) then
        raise exception 'RLS must remain enabled after provenance migration';
    end if;
end;
$$;
