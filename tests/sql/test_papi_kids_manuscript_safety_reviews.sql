begin;

do $$
declare
    table_exists boolean;
    rls_enabled boolean;
begin
    select exists (
        select 1 from information_schema.tables
        where table_schema = 'papi_kids_private'
          and table_name = 'manuscript_safety_reviews'
    ) into table_exists;
    if not table_exists then
        raise exception 'manuscript_safety_reviews table missing';
    end if;

    select relrowsecurity into rls_enabled
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'papi_kids_private'
       and c.relname = 'manuscript_safety_reviews';
    if not rls_enabled then
        raise exception 'RLS must be enabled for manuscript_safety_reviews';
    end if;

    if not exists (
        select 1 from information_schema.columns
         where table_schema = 'papi_kids_private'
           and table_name = 'manuscript_safety_reviews'
           and column_name = 'manuscript_sha256'
    ) then
        raise exception 'manuscript SHA-256 binding column missing';
    end if;

    if not exists (
        select 1 from information_schema.columns
         where table_schema = 'papi_kids_private'
           and table_name = 'manuscript_safety_reviews'
           and column_name = 'evidence_ref'
    ) then
        raise exception 'safety review evidence reference missing';
    end if;
end;
$$;

rollback;
