-- Rollback for 013_shared_provider_quota_ledger.sql
revoke all on function public.papi_release_provider_quota(uuid) from public, anon, authenticated, service_role;
revoke all on function public.papi_mark_provider_quota_uncertain(uuid) from public, anon, authenticated, service_role;
revoke all on function public.papi_commit_provider_quota(uuid,bigint) from public, anon, authenticated, service_role;
revoke all on function public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date) from public, anon, authenticated, service_role;
drop function if exists public.papi_release_provider_quota(uuid);
drop function if exists public.papi_mark_provider_quota_uncertain(uuid);
drop function if exists public.papi_commit_provider_quota(uuid,bigint);
drop function if exists public.papi_reserve_provider_quota(text,text,text,text,text,bigint,bigint,date);
drop table if exists public.papi_provider_quota_reservations;
drop table if exists public.papi_provider_daily_quotas;
