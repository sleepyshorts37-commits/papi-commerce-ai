begin;

do $$
declare
    table_exists boolean;
    rls_enabled boolean;
begin
    select exists (
        select 1 from information_schema.tables
        where table_schema = 'papi_kids_private'
          and table_name = 'kdp_package_reviews'
    ) into table_exists;
    if not table_exists then
        raise exception 'kdp_package_reviews table missing';
    end if;

    select relrowsecurity into rls_enabled
      from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'papi_kids_private'
       and c.relname = 'kdp_package_reviews';
    if not rls_enabled then
        raise exception 'RLS must be enabled for kdp_package_reviews';
    end if;

    if not exists (
        select 1 from information_schema.columns
         where table_schema = 'papi_kids_private'
           and table_name = 'kdp_package_reviews'
           and column_name = 'artifact_sha256'
    ) then
        raise exception 'artifact hash binding column missing';
    end if;
end;
$$;

rollback;
