-- Mission 30 incident response SQL contracts.
do $$
declare v_alert uuid; v_incident uuid; v_second_alert uuid; v_second_incident uuid; v_result jsonb; v_count integer;
begin
 perform public.papi_register_worker('CI-WORKER-M30','IDENTITY-CI-WORKER-M30','CI Worker M30','market','Incident Test Worker',null,
  array['test.run'],array['task.execute'],2);
 insert into public.papi_supervisor_alerts(alert_key,worker_id,severity,alert_type,summary,evidence,recommended_action)
 values('ci-m30-alert-key-001','CI-WORKER-M30','warning','failure_rate','Repeated execution failures require investigation.',
  '{"failure_count":4,"window":"1h"}'::jsonb,'review') returning alert_id into v_alert;

 v_result:=public.papi_incident_open_from_alert(v_alert,'ci-m30-incident-key-001','human-operator');
 v_incident:=(v_result->>'incident_id')::uuid;
 if (v_result->>'duplicate')::boolean then raise exception 'First incident creation was marked duplicate'; end if;
 if not exists(select 1 from public.papi_incidents where incident_id=v_incident and category='execution' and severity='high' and status='open')
 then raise exception 'Incident metadata was not mapped from alert'; end if;
 v_result:=public.papi_incident_open_from_alert(v_alert,'ci-m30-incident-key-001','human-operator');
 if (v_result->>'duplicate')::boolean is not true then raise exception 'Alert replay was not idempotent'; end if;

 begin
  perform public.papi_incident_transition(v_incident,'close','human-operator',null,'Premature close','{}'::jsonb,'ci-m30-invalid-transition');
  raise exception 'Incident was closed before resolution';
 exception when sqlstate '55000' then null; end;

 perform public.papi_incident_transition(v_incident,'assign','human-operator','human-manager',null,'{}'::jsonb,'ci-m30-assign-001');
 perform public.papi_incident_transition(v_incident,'qualify','human-manager',null,'Initial qualification','{"triage":"complete"}'::jsonb,'ci-m30-qualify-001');
 perform public.papi_incident_transition(v_incident,'investigate','human-manager',null,'Investigation started','{}'::jsonb,'ci-m30-investigate-001');
 perform public.papi_incident_transition(v_incident,'escalate','human-manager',null,'Additional failures confirmed','{"evidence_ref":"internal-log-1"}'::jsonb,'ci-m30-escalate-001');
 if not exists(select 1 from public.papi_incidents where incident_id=v_incident and severity='critical' and assigned_human='human-manager')
 then raise exception 'Human assignment or severity escalation failed'; end if;
 perform public.papi_incident_transition(v_incident,'mitigate','human-manager',null,'Containment completed','{"mitigation":"retry queue isolated"}'::jsonb,'ci-m30-mitigate-001');
 perform public.papi_incident_transition(v_incident,'resolve','human-manager',null,'Root cause corrected and verified','{"verification":"passed"}'::jsonb,'ci-m30-resolve-001');
 perform public.papi_incident_transition(v_incident,'close','human-manager',null,'Post-incident review completed','{"review":"approved"}'::jsonb,'ci-m30-close-001');
 if not exists(select 1 from public.papi_incidents where incident_id=v_incident and status='closed' and resolved_by='human-manager' and closed_by='human-manager')
 then raise exception 'Incident resolution or closure was not persisted'; end if;
 if (select count(*) from public.papi_incident_events where incident_id=v_incident)<7 then raise exception 'Incident event history is incomplete'; end if;

 begin
  update public.papi_incident_events set actor='tampered' where incident_id=v_incident;
  raise exception 'Append-only incident history accepted UPDATE';
 exception when sqlstate '55000' then null; end;
 begin
  delete from public.papi_incident_events where incident_id=v_incident;
  raise exception 'Append-only incident history accepted DELETE';
 exception when sqlstate '55000' then null; end;

 insert into public.papi_supervisor_alerts(alert_key,worker_id,severity,alert_type,summary,evidence,recommended_action)
 values('ci-m30-alert-key-002','CI-WORKER-M30','warning','stale_heartbeat','Worker heartbeat overdue.',
  '{"last_seen":"earlier"}'::jsonb,'review') returning alert_id into v_second_alert;
 v_result:=public.papi_incident_open_from_alert(v_second_alert,'ci-m30-incident-key-002','human-operator');
 v_second_incident:=(v_result->>'incident_id')::uuid;
 update public.papi_incidents set target_resolution_at=now()-interval '1 minute' where incident_id=v_second_incident;
 v_count:=public.papi_incident_detect_overdue('incident-monitor');
 if v_count<>1 then raise exception 'Overdue incident was not detected'; end if;
 if public.papi_incident_detect_overdue('incident-monitor')<>0 then raise exception 'SLA breach was not idempotent'; end if;
 if not exists(select 1 from public.papi_incident_events where incident_id=v_second_incident and event_type='sla_breached')
 then raise exception 'SLA breach event was not recorded'; end if;

 if has_table_privilege('anon','public.papi_incidents','select')
 or has_table_privilege('authenticated','public.papi_incident_events','select')
 or has_function_privilege('anon','public.papi_incident_open_from_alert(uuid,text,text)','execute')
 or has_function_privilege('authenticated','public.papi_incident_transition(uuid,text,text,text,text,jsonb,text)','execute')
 then raise exception 'Incident response privileges are too broad'; end if;
end; $$;
