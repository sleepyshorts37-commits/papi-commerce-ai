-- Mission 29 SQL contracts.
do $$
declare v_eval jsonb; v_heartbeat timestamptz; v_alert_id uuid;
begin
 insert into public.papi_tasks(id,task,version) values('CI-M29-TASK-001','{"id":"CI-M29-TASK-001","status":"ready"}'::jsonb,1);
 perform public.papi_register_worker('CI-WORKER-M29','IDENTITY-CI-WORKER-M29','CI Worker M29','market','Test Worker',null,
 array['test.run'],array['task.execute'],3);
 perform public.papi_set_worker_status('CI-WORKER-M29','active');
 v_heartbeat:=public.papi_supervisor_heartbeat('CI-WORKER-M29','worker_runtime');
 if v_heartbeat is null or not exists(select 1 from public.papi_worker_heartbeats where worker_id='CI-WORKER-M29' and last_seen_at=v_heartbeat)
 then raise exception 'Heartbeat was not recorded'; end if;
 v_eval:=public.papi_supervisor_evaluate_worker('CI-WORKER-M29','supervisor-ci',now()-interval '1 day',now()+interval '1 second');
 if (v_eval->>'sample_size')::integer<>0 or (v_eval->>'overall_score')::numeric<>100 then raise exception 'Empty sample baseline is incorrect'; end if;
 begin
  perform public.papi_supervisor_evaluate_worker('CI-WORKER-M29','CI-WORKER-M29',now()-interval '1 day',now()+interval '1 second');
  raise exception 'Self-evaluation was accepted';
 exception when invalid_parameter_value then null; end;
 insert into public.papi_supervisor_alerts(alert_key,worker_id,severity,alert_type,summary,evidence,recommended_action)
 values('ci-m29-human-review-001','CI-WORKER-M29','warning','low_score','CI human review alert','{"source":"test"}'::jsonb,'review')
 returning alert_id into v_alert_id;
 if not public.papi_supervisor_update_alert(v_alert_id,'acknowledge','human-reviewer') then raise exception 'Human acknowledgement failed'; end if;
 if not exists(select 1 from public.papi_supervisor_alerts where alert_id=v_alert_id and status='acknowledged' and acknowledged_by='human-reviewer')
 then raise exception 'Human acknowledgement was not persisted'; end if;
 if (select status from public.papi_workers where worker_id='CI-WORKER-M29')<>'active' then raise exception 'Supervisor unexpectedly changed worker status'; end if;
 if has_table_privilege('anon','public.papi_worker_evaluations','select')
 or has_table_privilege('authenticated','public.papi_supervisor_alerts','select')
 or has_function_privilege('anon','public.papi_supervisor_evaluate_worker(text,text,timestamptz,timestamptz)','execute')
 or has_function_privilege('authenticated','public.papi_supervisor_update_alert(uuid,text,text)','execute')
 then raise exception 'Supervisor permissions are too broad'; end if;
end; $$;
