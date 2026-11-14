-- Disposable local test roles only. Never use these credentials in production.
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
