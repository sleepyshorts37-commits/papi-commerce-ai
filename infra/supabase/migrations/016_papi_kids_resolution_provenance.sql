-- Preserve original resolution and human approval of super-resolution outputs.
alter table papi_kids_private.illustration_assets
    add column if not exists source_width_px integer,
    add column if not exists source_height_px integer,
    add column if not exists upscaling_method text not null default 'native',
    add column if not exists resolution_reviewed_by text,
    add column if not exists resolution_reviewed_at timestamptz,
    add column if not exists resolution_review_output_sha256 text;

update papi_kids_private.illustration_assets
   set source_width_px = coalesce(source_width_px, width_px),
       source_height_px = coalesce(source_height_px, height_px);

alter table papi_kids_private.illustration_assets
    alter column source_width_px set not null,
    alter column source_height_px set not null;

alter table papi_kids_private.illustration_assets
    drop constraint if exists illustration_assets_upscaling_method_check,
    add constraint illustration_assets_upscaling_method_check
        check (upscaling_method in ('native','ai_super_resolution','manual_retouch','lanczos_only')),
    drop constraint if exists illustration_assets_source_dimensions_check,
    add constraint illustration_assets_source_dimensions_check
        check (source_width_px > 0 and source_width_px <= 12000
           and source_height_px > 0 and source_height_px <= 12000),
    drop constraint if exists illustration_assets_resolution_hash_check,
    add constraint illustration_assets_resolution_hash_check
        check (resolution_review_output_sha256 is null
            or resolution_review_output_sha256 ~ '^[0-9a-f]{64}$');

create index if not exists illustration_assets_resolution_review_idx
    on papi_kids_private.illustration_assets (upscaling_method, resolution_reviewed_at);
