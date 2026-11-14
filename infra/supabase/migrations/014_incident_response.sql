-- Mission 30: controlled incident response and human-led recovery.
create table if not exists public.papi_incidents (
 incident_id uuid primary key default gen_random_uuid(),
 incident_key text not null unique check(length(trim(incident_key)) between 8 and 200),
 source_alert_id uuid unique references public.papi_supervisor_alerts(alert_id) on delete restrict,
 worker_id text references public.papi_workers(worker_id) on delete restrict,
 job_id text references public.papi_jobs(id) on delete restrict,
 category text not null check(category in('availability','execution','security','quality','data','integration','performance','other')),
 severity text not null check(severity in('low','medium','high','critical')),
 status text not null default 'open' check(status in('open','qualified','investigating','mitigated','resolved','closed')),
 title text not null check(length(trim(title)) between 3 and 200),
 summary text not null check(length(trim(summary)) between 1 and 4000),
 evidence jsonb not null default '{}'::jsonb check(jsonb_typeof(evidence)='object'),
 assigned_human text check(assigned_human is null or length(trim(assigned_human)) between 1 and 160),
 created_by text not null check(length(trim(created_by)) between 1 and 160),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 target_resolution_at timestamptz not null,
 sla_breached_at timestamptz,
 resolved_at timestamptz, resolved_by text, resolution_summary text,
 closed_at timestamptz, closed_by text,
 check((resolved_at is null)=(resolved_by is null)),
 check((closed_at is null)=(closed_by is null)),
 check(status not in('resolved','closed') or (resolved_at is not null and length(trim(coalesce(resolution_summary,'')))>=5)),
 check(status<>'closed' or closed_at is not null),
 check(status not in('open','qualified','investigating','mitigated') or closed_at is null)
);
create index if not exists papi_incidents_status_severity_idx on public.papi_incidents(status,severity,target_resolution_at);
create index if not exists papi_incidents_worker_history_idx on public.papi_incidents(worker_id,created_at desc);
create index if not exists papi_incidents_assignee_idx on public.papi_incidents(assigned_human,status,created_at desc);

create table if not exists public.papi_incident_events (
 event_id uuid primary key default gen_random_uuid(),
 incident_id uuid not null references public.papi_incidents(incident_id) on delete restrict,
 event_key text not null unique check(length(trim(event_key)) between 8 and 220),
 event_type text not null check(event_type in('created','qualified','investigating','mitigated','assigned','escalated','sla_breached','resolved','reopened','closed','evidence_added')),
 actor text not null check(length(trim(actor)) between 1 and 160),
 from_status text,
 to_status text,
 details jsonb not null default '{}'::jsonb check(jsonb_typeof(details)='object'),
 occurred_at timestamptz not null default now()
);
create index if not exists papi_incident_events_history_idx on public.papi_incident_events(incident_id,occurred_at,event_id);

alter table public.papi_incidents enable row level security;
alter table public.papi_incident_events enable row level security;
revoke all on public.papi_incidents from public,anon,authenticated;
revoke all on public.papi_incident_events from public,anon,authenticated;
grant select on public.papi_incidents to service_role;
grant select on public.papi_incident_events to service_role;

create or replace function public.papi_reject_incident_event_mutation()
returns trigger language plpgsql set search_path=public,pg_temp as $$
begin raise exception 'Incident events are append-only' using errcode='55000'; end; $$;
create trigger papi_incident_events_append_only
 before update or delete on public.papi_incident_events
 for each row execute function public.papi_reject_incident_event_mutation();

create or replace function public.papi_incident_sla_interval(p_severity text)
returns interval language sql immutable strict as $$
 select case p_severity when 'critical' then interval '1 hour'
 when 'high' then interval '4 hours' when 'medium' then interval '24 hours'
 else interval '72 hours' end
$$;

-- Convert one supervisor alert into one incident. Replays return the existing incident.
create or replace function public.papi_incident_open_from_alert(
 p_alert_id uuid,p_incident_key text,p_actor text
) returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_alert public.papi_supervisor_alerts%rowtype; v_incident public.papi_incidents%rowtype; v_category text; v_severity text;
begin
 if p_alert_id is null or p_incident_key is null or length(trim(p_incident_key)) not between 8 and 200
 or p_actor is null or length(trim(p_actor)) not between 1 and 160 then
  raise exception 'Invalid incident creation request' using errcode='22023';
 end if;
 perform pg_advisory_xact_lock(hashtextextended(p_incident_key,30));
 select * into v_alert from public.papi_supervisor_alerts where alert_id=p_alert_id for update;
 if not found then raise exception 'Source alert not found' using errcode='23503'; end if;
 select * into v_incident from public.papi_incidents where source_alert_id=p_alert_id;
 if found then
  if v_incident.incident_key<>p_incident_key then raise exception 'Alert already linked to a different incident key' using errcode='23505'; end if;
  return jsonb_build_object('incident_id',v_incident.incident_id,'duplicate',true,'status',v_incident.status);
 end if;
 select * into v_incident from public.papi_incidents where incident_key=p_incident_key;
 if found then raise exception 'Incident key already belongs to another incident' using errcode='23505'; end if;
 v_category:=case v_alert.alert_type when 'stale_heartbeat' then 'availability'
 when 'failure_rate' then 'execution' when 'repeated_failures' then 'execution'
 when 'low_score' then 'quality' else 'other' end;
 v_severity:=case v_alert.severity when 'critical' then 'critical' when 'warning' then 'high' else 'low' end;
 insert into public.papi_incidents(incident_key,source_alert_id,worker_id,category,severity,title,summary,evidence,created_by,target_resolution_at)
 values(p_incident_key,p_alert_id,v_alert.worker_id,v_category,v_severity,
 'Incident from supervisor alert: '||v_alert.alert_type,v_alert.summary,
 v_alert.evidence||jsonb_build_object('source_alert_id',p_alert_id,'recommended_action',v_alert.recommended_action),
 p_actor,now()+public.papi_incident_sla_interval(v_severity))
 returning * into v_incident;
 insert into public.papi_incident_events(incident_id,event_key,event_type,actor,to_status,details)
 values(v_incident.incident_id,'incident-created:'||v_incident.incident_id::text,'created',p_actor,'open',
 jsonb_build_object('source_alert_id',p_alert_id,'severity',v_severity,'category',v_category));
 insert into public.papi_audit_events(event_id,occurred_at,actor,action,entity_type,entity_id,details)
 values('incident-created:'||v_incident.incident_id::text,now(),p_actor,'incident.created','incident',v_incident.incident_id::text,
 jsonb_build_object('source_alert_id',p_alert_id,'severity',v_severity,'category',v_category));
 return jsonb_build_object('incident_id',v_incident.incident_id,'duplicate',false,'status',v_incident.status);
end; $$;

create or replace function public.papi_incident_transition(
 p_incident_id uuid,p_action text,p_actor text,p_owner text default null,
 p_summary text default null,p_evidence jsonb default '{}'::jsonb,p_event_key text default null
) returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_incident public.papi_incidents%rowtype; v_existing_event public.papi_incident_events%rowtype; v_new_status text; v_new_severity text; v_event_type text; v_details jsonb; v_expected_owner text;
begin
 if p_incident_id is null or p_action is null or p_action not in('qualify','investigate','mitigate','assign','escalate','resolve','reopen','close','add_evidence')
 or p_actor is null or length(trim(p_actor)) not between 1 and 160
 or p_evidence is null or jsonb_typeof(p_evidence)<>'object'
 or (p_event_key is not null and length(trim(p_event_key)) not between 8 and 220) then
  raise exception 'Invalid incident transition request' using errcode='22023';
 end if;
 if p_action='assign' and (p_owner is null or length(trim(p_owner)) not between 1 and 160) then
  raise exception 'A human owner is required' using errcode='22023';
 end if;
 if p_action in('resolve','close') and (p_summary is null or length(trim(p_summary))<5) then
  raise exception 'Resolution or closure requires a meaningful summary' using errcode='22023';
 end if;
 select * into v_incident from public.papi_incidents where incident_id=p_incident_id for update;
 if not found then raise exception 'Incident not found' using errcode='23503'; end if;
 v_event_type:=case p_action when 'qualify' then 'qualified' when 'investigate' then 'investigating' when 'mitigate' then 'mitigated' when 'escalate' then 'escalated' when 'reopen' then 'reopened' when 'resolve' then 'resolved' when 'close' then 'closed' when 'add_evidence' then 'evidence_added' else p_action end;
 v_expected_owner:=case when p_action='assign' then p_owner else null end;
 if p_event_key is not null then
  select * into v_existing_event from public.papi_incident_events where event_key=p_event_key;
  if found then
   if v_existing_event.incident_id<>p_incident_id or v_existing_event.actor<>p_actor or v_existing_event.event_type<>v_event_type
    or v_existing_event.details->>'action' is distinct from p_action or v_existing_event.details->>'summary' is distinct from p_summary
    or v_existing_event.details->>'owner' is distinct from v_expected_owner
    or v_existing_event.details->'evidence' is distinct from p_evidence then
    raise exception 'Incident event key reused with different intent' using errcode='23505';
   end if;
   return jsonb_build_object('incident_id',p_incident_id,'duplicate',true,'status',v_incident.status);
  end if;
 end if;
 v_new_status:=v_incident.status; v_new_severity:=v_incident.severity;
 if p_action='qualify' and v_incident.status='open' then v_new_status:='qualified';
 elsif p_action='investigate' and v_incident.status in('open','qualified') then v_new_status:='investigating';
 elsif p_action='mitigate' and v_incident.status in('investigating','qualified') then v_new_status:='mitigated';
 elsif p_action='resolve' and v_incident.status in('investigating','mitigated','qualified') then v_new_status:='resolved';
 elsif p_action='close' and v_incident.status='resolved' then v_new_status:='closed';
 elsif p_action='reopen' and v_incident.status='resolved' then v_new_status:='investigating';
 elsif p_action='assign' and v_incident.status not in('closed','resolved') then v_event_type:='assigned';
 elsif p_action='add_evidence' and v_incident.status<>'closed' then v_event_type:='evidence_added';
 elsif p_action='escalate' and v_incident.status not in('closed','resolved') then
  v_new_severity:=case v_incident.severity when 'low' then 'medium' when 'medium' then 'high' when 'high' then 'critical' else 'critical' end;
  if v_new_severity=v_incident.severity then raise exception 'Incident is already at maximum severity' using errcode='22023'; end if;
 else raise exception 'Invalid incident state transition' using errcode='55000';
 end if;
 if p_action='resolve' then
  update public.papi_incidents set status=v_new_status,updated_at=now(),resolved_at=now(),resolved_by=p_actor,resolution_summary=p_summary,
   evidence=evidence||p_evidence where incident_id=p_incident_id;
 elsif p_action='close' then
  update public.papi_incidents set status=v_new_status,updated_at=now(),closed_at=now(),closed_by=p_actor,evidence=evidence||p_evidence where incident_id=p_incident_id;
 elsif p_action='reopen' then
  update public.papi_incidents set status=v_new_status,updated_at=now(),resolved_at=null,resolved_by=null,resolution_summary=null,evidence=evidence||p_evidence,
   target_resolution_at=now()+public.papi_incident_sla_interval(v_incident.severity) where incident_id=p_incident_id;
 elsif p_action='assign' then
  update public.papi_incidents set assigned_human=p_owner,updated_at=now(),evidence=evidence||p_evidence where incident_id=p_incident_id;
 elsif p_action='escalate' then
  update public.papi_incidents set severity=v_new_severity,updated_at=now(),
   target_resolution_at=least(target_resolution_at,now()+public.papi_incident_sla_interval(v_new_severity)),evidence=evidence||p_evidence where incident_id=p_incident_id;
 else
  update public.papi_incidents set status=v_new_status,updated_at=now(),evidence=evidence||p_evidence where incident_id=p_incident_id;
 end if;
 v_details:=jsonb_build_object('action',p_action,'summary',p_summary,'owner',case when p_action='assign' then p_owner else null end,'evidence',p_evidence,'severity',v_new_severity);
 insert into public.papi_incident_events(incident_id,event_key,event_type,actor,from_status,to_status,details)
 values(p_incident_id,coalesce(p_event_key,'incident-event:'||gen_random_uuid()::text),v_event_type,p_actor,v_incident.status,v_new_status,v_details);
 insert into public.papi_audit_events(event_id,occurred_at,actor,action,entity_type,entity_id,details)
 values('incident-audit:'||gen_random_uuid()::text,now(),p_actor,'incident.'||p_action,'incident',p_incident_id::text,v_details);
 return jsonb_build_object('incident_id',p_incident_id,'duplicate',false,'status',v_new_status,'severity',v_new_severity);
end; $$;

create or replace function public.papi_incident_detect_overdue(p_actor text)
returns integer language plpgsql security definer set search_path=public,pg_temp as $$
declare v_count integer;
begin
 if p_actor is null or length(trim(p_actor)) not between 1 and 160 then raise exception 'Invalid incident monitor actor' using errcode='22023'; end if;
 with overdue as (
  update public.papi_incidents set sla_breached_at=now(),updated_at=now()
   where status not in('resolved','closed') and target_resolution_at<now() and sla_breached_at is null
   returning incident_id,status,severity,target_resolution_at,assigned_human
 ), events as (
  insert into public.papi_incident_events(incident_id,event_key,event_type,actor,from_status,to_status,details)
  select incident_id,'incident-sla-breach:'||incident_id::text,'sla_breached',p_actor,status,status,
   jsonb_build_object('severity',severity,'target_resolution_at',target_resolution_at,'assigned_human',assigned_human)
  from overdue returning incident_id
 ), audited as (
  insert into public.papi_audit_events(event_id,occurred_at,actor,action,entity_type,entity_id,details)
  select 'incident-sla-audit:'||incident_id::text,now(),p_actor,'incident.sla_breached','incident',incident_id::text,'{}'::jsonb
  from events returning entity_id
 )
 select count(*) into v_count from audited;
 return v_count;
end; $$;

revoke all on function public.papi_reject_incident_event_mutation() from public,anon,authenticated;
revoke all on function public.papi_incident_sla_interval(text) from public,anon,authenticated;
revoke all on function public.papi_incident_open_from_alert(uuid,text,text) from public,anon,authenticated;
revoke all on function public.papi_incident_transition(uuid,text,text,text,text,jsonb,text) from public,anon,authenticated;
revoke all on function public.papi_incident_detect_overdue(text) from public,anon,authenticated;
grant execute on function public.papi_incident_open_from_alert(uuid,text,text) to service_role;
grant execute on function public.papi_incident_transition(uuid,text,text,text,text,jsonb,text) to service_role;
grant execute on function public.papi_incident_detect_overdue(text) to service_role;
