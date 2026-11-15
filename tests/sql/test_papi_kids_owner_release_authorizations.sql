begin;

do $$
declare
    enabled boolean;
begin
    if not exists (
        select 1 from information_schema.tables
        where table_schema = 'papi_kids_private'
          and table_name = 'kdp_owner_release_authorizations'
    ) then
        raise exception 'owner release authorization table missing';
    end if;
    select relrowsecurity into enabled
      from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'papi_kids_private'
       and c.relname = 'kdp_owner_release_authorizations';
    if not enabled then
        raise exception 'RLS must be enabled';
    end if;
end;
$$;

rollback;
