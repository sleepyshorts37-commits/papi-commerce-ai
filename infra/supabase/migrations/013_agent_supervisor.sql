-- Mission 29: operational supervision, explainable evaluations and human-routed alerts.
-- This migration observes worker execution only. It never activates, pauses or disables workers.
create table if not exists public.papi_worker_heartbeats (
 worker_id text primary key references public.papi_workers(worker_id) on delete restrict,
 last_seen_at timestamptz not null, source text not null check (source in ('worker_runtime','trusted_monitor')),
 updated_at timestamptz not null default now()
);
create table if not exists public.papi_worker_evaluations (
 evaluation_id uuid primary key default gen_random_uuid(),
 worker_id text not null references public.papi_workers(worker_id) on delete restrict,
 evaluator_id text not null check (length(trim(evaluator_id)) between 1 and 120),
 period_start timestamptz not null, period_end timestamptz not null,
 sample_size integer not null check (sample_size >= 0),
 completed_count integer not null check (completed_count >= 0),
 failed_count integer not null check (failed_count >= 0),
 reliability_score numeric(5,2) not null check (reliability_score between 0 and 100),
 completion_score numeric(5,2) not null check (completion_score between 0 and 100),
 timeliness_score numeric(5,2) not null check (timeliness_score between 0 and 100),
 overall_score numeric(5,2) not null check (overall_score between 0 and 100),
 methodology_version text not null default 'operational-v1',
 explanation jsonb not null check (jsonb_typeof(explanation) = 'object'),
 created_at timestamptz not null default now(),
 check (period_end > period_start),
 check (completed_count + failed_count <= sample_size)
);
create index if not exists papi_worker_evaluations_history_idx on public.papi_worker_evaluations(worker_id, created_at desc);
create table if not exists public.papi_supervisor_alerts (
 alert_id uuid primary key default gen_random_uuid(),
 alert_key text not null unique check (length(alert_key) between 8 and 200),
 worker_id text not null references public.papi_workers(worker_id) on delete restrict,
 manager_worker_id text references public.papi_workers(worker_id) on delete restrict,
 severity text not null check (severity in ('info','warning','critical')),
 alert_type text not null check (alert_type in ('failure_rate','stale_heartbeat','low_score','repeated_failures')),
 status text not null default 'open' check (status in ('open','acknowledged','resolved')),
 summary text not null check (length(trim(summary)) between 1 and 500),
 evidence jsonb not null check (jsonb_typeof(evidence) = 'object'),
 recommended_action text not null check (recommended_action in ('review','coach','consider_pause')),
 created_at timestamptz not null default now(),
 acknowledged_at timestamptz, acknowledged_by text, resolved_at timestamptz, resolved_by text,
 check ((acknowledged_at is null) = (acknowledged_by is null)),
 check ((resolved_at is null) = (resolved_by is null)),
 check (status <> 'resolved' or resolved_at is not null)
);
create index if not exists papi_supervisor_alerts_routing_idx on public.papi_supervisor_alerts(manager_worker_id,status,severity,created_at desc);
create index if not exists papi_supervisor_alerts_worker_idx on public.papi_supervisor_alerts(worker_id,created_at desc);
create unique index if not exists papi_supervisor_one_open_alert_per_type_idx
 on public.papi_supervisor_alerts(worker_id,alert_type) where status in ('open','acknowledged');
alter table public.papi_worker_heartbeats enable row level security;
alter table public.papi_worker_evaluations enable row level security;
alter table public.papi_supervisor_alerts enable row level security;
revoke all on public.papi_worker_heartbeats from public,anon,authenticated;
revoke all on public.papi_worker_evaluations from public,anon,authenticated;
revoke all on public.papi_supervisor_alerts from public,anon,authenticated;
grant select on public.papi_worker_heartbeats to service_role;
grant select on public.papi_worker_evaluations to service_role;
grant select on public.papi_supervisor_alerts to service_role;

create or replace function public.papi_supervisor_heartbeat(p_worker_id text,p_source text default 'worker_runtime')
returns timestamptz language plpgsql security definer set search_path=public,pg_temp as $$
declare v_seen timestamptz:=now();
begin
 if p_worker_id is null or p_source is null or p_source not in ('worker_runtime','trusted_monitor') then raise exception 'Invalid supervisor heartbeat' using errcode='22023'; end if;
 if not exists(select 1 from public.papi_workers where worker_id=p_worker_id) then raise exception 'Unknown worker' using errcode='23503'; end if;
 insert into public.papi_worker_heartbeats(worker_id,last_seen_at,source,updated_at) values(p_worker_id,v_seen,p_source,v_seen)
 on conflict(worker_id) do update set last_seen_at=greatest(public.papi_worker_heartbeats.last_seen_at,excluded.last_seen_at),source=excluded.source,updated_at=v_seen;
 return v_seen;
end; $$;

-- Operational proxy: 50% reliability, 30% terminal-outcome coverage, 20% runtime timeliness.
-- This is not a customer-quality or revenue score.
create or replace function public.papi_supervisor_evaluate_worker(
 p_worker_id text,p_evaluator_id text,p_period_start timestamptz default now()-interval '30 days',p_period_end timestamptz default now()
) returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_sample integer; v_terminal integer; v_completed integer; v_failed integer; v_reliability numeric(5,2); v_completion numeric(5,2);
 v_timeliness numeric(5,2); v_overall numeric(5,2); v_eval uuid; v_durations numeric;
begin
 if p_worker_id is null or p_evaluator_id is null or length(trim(p_evaluator_id)) not between 1 and 120
 or p_worker_id=p_evaluator_id or p_period_start is null or p_period_end is null or p_period_end<=p_period_start
 or p_period_end>now()+interval '60 seconds' or p_period_end-p_period_start>interval '366 days'
 then raise exception 'Invalid or self evaluation request' using errcode='22023'; end if;
 if not exists(select 1 from public.papi_workers where worker_id=p_worker_id) then raise exception 'Unknown worker' using errcode='23503'; end if;
 select count(*),count(*) filter(where a.status in('completed','failed')),
 count(*) filter(where a.status='completed'),count(*) filter(where a.status='failed'),
 avg(extract(epoch from(a.finished_at-a.started_at))/60.0) filter(where a.status in('completed','failed'))
 into v_sample,v_terminal,v_completed,v_failed,v_durations
 from public.papi_worker_assignments a where a.worker_id=p_worker_id and a.assigned_at>=p_period_start and a.assigned_at<p_period_end;
 v_reliability:=case when v_terminal=0 then 100 else round(100.0*v_completed/v_terminal,2) end;
 v_completion:=case when v_sample=0 then 100 else round(100.0*v_terminal/v_sample,2) end;
 v_timeliness:=case when v_durations is null then 100 else round(greatest(0,least(100,100-(v_durations/60.0*100))),2) end;
 v_overall:=round(v_reliability*0.50+v_completion*0.30+v_timeliness*0.20,2);
 insert into public.papi_worker_evaluations(worker_id,evaluator_id,period_start,period_end,sample_size,completed_count,failed_count,
 reliability_score,completion_score,timeliness_score,overall_score,explanation)
 values(p_worker_id,p_evaluator_id,p_period_start,p_period_end,v_sample,v_completed,v_failed,v_reliability,v_completion,v_timeliness,v_overall,
 jsonb_build_object('methodology','operational-v1','weights',jsonb_build_object('reliability',0.50,'completion',0.30,'timeliness',0.20),
 'duration_target_minutes',60,'duration_average_minutes',v_durations,'sample_size',v_sample,
 'limitations','No direct customer-quality or revenue attribution is inferred.'))
 returning evaluation_id into v_eval;
 insert into public.papi_audit_events(event_id,occurred_at,actor,action,entity_type,entity_id,details)
 values('supervisor-eval:'||v_eval::text,now(),p_evaluator_id,'worker.evaluated','worker',p_worker_id,
 jsonb_build_object('evaluation_id',v_eval,'overall_score',v_overall,'sample_size',v_sample));
 if v_terminal>=3 and v_reliability<70 then
  insert into public.papi_supervisor_alerts(alert_key,worker_id,manager_worker_id,severity,alert_type,summary,evidence,recommended_action)
  select 'failure-rate:'||p_worker_id||':'||to_char(p_period_end at time zone 'UTC','YYYYMMDDHH24MI'),p_worker_id,w.manager_worker_id,
  'critical','failure_rate','Worker failure rate requires human review.',
  jsonb_build_object('sample_size',v_sample,'completed',v_completed,'failed',v_failed,'reliability_score',v_reliability),'review'
  from public.papi_workers w where w.worker_id=p_worker_id on conflict(worker_id,alert_type) where status in('open','acknowledged') do nothing;
 end if;
 if v_terminal>=3 and v_overall<60 then
  insert into public.papi_supervisor_alerts(alert_key,worker_id,manager_worker_id,severity,alert_type,summary,evidence,recommended_action)
  select 'low-score:'||p_worker_id||':'||to_char(p_period_end at time zone 'UTC','YYYYMMDDHH24MI'),p_worker_id,w.manager_worker_id,
  'warning','low_score','Worker operational score is below the review threshold.',
  jsonb_build_object('overall_score',v_overall,'sample_size',v_sample),'coach'
  from public.papi_workers w where w.worker_id=p_worker_id on conflict(alert_key) do nothing;
 end if;
 return jsonb_build_object('evaluation_id',v_eval,'worker_id',p_worker_id,'sample_size',v_sample,'completed',v_completed,'failed',v_failed,
 'reliability_score',v_reliability,'completion_score',v_completion,'timeliness_score',v_timeliness,'overall_score',v_overall,'methodology','operational-v1');
end; $$;

create or replace function public.papi_supervisor_detect_stale_workers(p_evaluator_id text,p_stale_after_seconds integer default 300)
returns integer language plpgsql security definer set search_path=public,pg_temp as $$
declare v_count integer;
begin
 if p_evaluator_id is null or length(trim(p_evaluator_id)) not between 1 and 120 or p_stale_after_seconds is null or p_stale_after_seconds not between 60 and 86400
 then raise exception 'Invalid stale-worker detection request' using errcode='22023'; end if;
 insert into public.papi_supervisor_alerts(alert_key,worker_id,manager_worker_id,severity,alert_type,summary,evidence,recommended_action)
 select 'stale-heartbeat:'||w.worker_id||':'||to_char(coalesce(h.last_seen_at,w.created_at) at time zone 'UTC','YYYYMMDDHH24MI'),
 w.worker_id,w.manager_worker_id,'warning','stale_heartbeat','Worker heartbeat is older than the configured observation window.',
 jsonb_build_object('last_seen_at',h.last_seen_at,'stale_after_seconds',p_stale_after_seconds),'review'
 from public.papi_workers w left join public.papi_worker_heartbeats h on h.worker_id=w.worker_id
 where w.status in('idle','active') and coalesce(h.last_seen_at,w.created_at)<now()-make_interval(secs=>p_stale_after_seconds)
 on conflict(worker_id,alert_type) where status in('open','acknowledged') do nothing;
 get diagnostics v_count=row_count; return v_count;
end; $$;

create or replace function public.papi_supervisor_update_alert(p_alert_id uuid,p_action text,p_human_actor text)
returns boolean language plpgsql security definer set search_path=public,pg_temp as $$
declare v_count integer;
begin
 if p_alert_id is null or p_action is null or p_action not in('acknowledge','resolve') or p_human_actor is null or length(trim(p_human_actor)) not between 1 and 120
 then raise exception 'Invalid alert update request' using errcode='22023'; end if;
 update public.papi_supervisor_alerts set status=case when p_action='resolve' then 'resolved' else 'acknowledged' end,
 acknowledged_at=case when p_action='acknowledge' then now() else acknowledged_at end,
 acknowledged_by=case when p_action='acknowledge' then p_human_actor else acknowledged_by end,
 resolved_at=case when p_action='resolve' then now() else resolved_at end,
 resolved_by=case when p_action='resolve' then p_human_actor else resolved_by end
 where alert_id=p_alert_id and ((p_action='acknowledge' and status='open') or (p_action='resolve' and status in('open','acknowledged')));
 get diagnostics v_count=row_count;
 if v_count=1 then
  insert into public.papi_audit_events(event_id,occurred_at,actor,action,entity_type,entity_id,details)
  values('supervisor-alert:'||p_alert_id::text||':'||p_action,now(),p_human_actor,'supervisor.alert_'||p_action,
  'supervisor_alert',p_alert_id::text,jsonb_build_object('action',p_action));
 end if;
 return v_count=1;
end; $$;

revoke all on function public.papi_supervisor_heartbeat(text,text) from public,anon,authenticated;
revoke all on function public.papi_supervisor_evaluate_worker(text,text,timestamptz,timestamptz) from public,anon,authenticated;
revoke all on function public.papi_supervisor_detect_stale_workers(text,integer) from public,anon,authenticated;
revoke all on function public.papi_supervisor_update_alert(uuid,text,text) from public,anon,authenticated;
grant execute on function public.papi_supervisor_heartbeat(text,text) to service_role;
grant execute on function public.papi_supervisor_evaluate_worker(text,text,timestamptz,timestamptz) to service_role;
grant execute on function public.papi_supervisor_detect_stale_workers(text,integer) to service_role;
grant execute on function public.papi_supervisor_update_alert(uuid,text,text) to service_role;
