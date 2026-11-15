-- PAPI shared provider quota: read-only reconciliation audit.
-- Safe to run with a read-only database role that can SELECT the quota tables.
-- This script never updates, releases, commits, or deletes reservations.

-- 1) Bucket-level accounting drift.
with reservation_totals as (
    select provider, account_ref, model, quota_day,
           coalesce(sum(estimated_units) filter (where status in ('reserved','uncertain')), 0)::bigint
               as open_reservation_units,
           count(*) filter (where status = 'uncertain')::bigint as uncertain_count,
           count(*) filter (where status = 'reserved')::bigint as reserved_count,
           min(created_at) filter (where status in ('reserved','uncertain')) as oldest_open_at
      from public.papi_provider_quota_reservations
     group by provider, account_ref, model, quota_day
)
select q.provider, q.account_ref, q.model, q.quota_day,
       q.daily_limit, q.reserved_units, q.consumed_units,
       coalesce(r.open_reservation_units, 0) as open_reservation_units,
       q.reserved_units - coalesce(r.open_reservation_units, 0) as reserved_drift_units,
       coalesce(r.uncertain_count, 0) as uncertain_count,
       coalesce(r.reserved_count, 0) as reserved_count,
       r.oldest_open_at,
       case
         when q.reserved_units <> coalesce(r.open_reservation_units, 0) then 'ACCOUNTING_DRIFT'
         when q.reserved_units + q.consumed_units > q.daily_limit then 'LIMIT_BREACH'
         when r.oldest_open_at < now() - interval '24 hours' then 'OPEN_OVER_24H'
         when r.oldest_open_at < now() - interval '1 hour' then 'OPEN_OVER_1H'
         else 'NORMAL_OR_RECENT'
       end as audit_class
  from public.papi_provider_daily_quotas q
  left join reservation_totals r
    using (provider, account_ref, model, quota_day)
 where q.reserved_units <> coalesce(r.open_reservation_units, 0)
    or q.reserved_units + q.consumed_units > q.daily_limit
    or r.oldest_open_at < now() - interval '1 hour'
 order by
       case when q.reserved_units <> coalesce(r.open_reservation_units, 0)
                  or q.reserved_units + q.consumed_units > q.daily_limit then 0 else 1 end,
       r.oldest_open_at asc nulls last;

-- 2) Reservation-level queue for human investigation.
select reservation_id, idempotency_key, provider, account_ref, model,
       quota_day, worker_id, estimated_units, actual_units, status,
       created_at, updated_at,
       floor(extract(epoch from (now() - created_at)) / 60)::bigint as age_minutes,
       case
         when status = 'uncertain' and created_at < now() - interval '24 hours'
           then 'URGENT_RECONCILIATION'
         when status = 'uncertain' and created_at < now() - interval '1 hour'
           then 'RECONCILE'
         when status = 'uncertain' then 'WAIT_OR_INVESTIGATE'
         when status = 'reserved' and created_at < now() - interval '1 hour'
           then 'CHECK_SUBMISSION_STATE'
         else 'NO_ACTION'
       end as recommended_review
  from public.papi_provider_quota_reservations
 where status in ('reserved','uncertain')
 order by created_at asc;
