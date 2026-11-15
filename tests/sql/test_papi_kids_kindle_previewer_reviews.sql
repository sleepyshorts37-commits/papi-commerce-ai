begin;

do $$
declare
    table_exists boolean;
    rls_enabled boolean;
begin
    select exists (
        select 1 from information_schema.tables
        where table_schema = 'papi_kids_private'
          and table_name = 'kindle_previewer_reviews'
    ) into table_exists;
    if not table_exists then
        raise exception 'kindle_previewer_reviews table missing';
    end if;

    select relrowsecurity into rls_enabled
      from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'papi_kids_private'
       and c.relname = 'kindle_previewer_reviews';
    if not rls_enabled then
        raise exception 'RLS must be enabled for kindle_previewer_reviews';
    end if;
end;
$$;

rollback;
