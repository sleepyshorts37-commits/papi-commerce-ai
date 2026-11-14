-- Mission 29 SQL contracts.
do $$
declare v_eval jsonb; v_heartbeat timestamptz; v_alert_id uuid; v_stale_count integer;
begin
 insert into public.papi_tasks(id,task,version) values('CI-M29-TASK-001','{"id":"CI-M29-TASK-001","status":"ready"}'::jsonb,1);
 perform public.papi_register_worker('CI-WORKER-M29','IDENTITY-CI-WORKER-M29','CI Worker M29','market','Test Worker',null,
 array['test.run'],array['task.execute'],3);
 perform public.papi_set_worker_status('CI-WORKER-M29','active');
 v_heartbeat:=public.papi_supervisor_heartbeat('CI-WORKER-M29','worker_runtime');
 if v_heartbeat is null or not exists(select 1 from public.papi_worker_heartbeats where worker_id='CI-WORKER-M29' and last_seen_at=v_heartbeat)
 then raise exception 'Heartbeat was not recorded'; end if;

 -- Add three assignments: one successful, one failed and one still open.
 insert into public.papi_jobs(id,task_id,handler,payload,idempotency_key,status,attempts,max_attempts)
 values
 ('JOB-CI-M29-001','CI-M29-TASK-001','test.run','{}'::jsonb,'ci-m29-job-key-001','done',1,3),
 ('JOB-CI-M29-002','CI-M29-TASK-001','test.run','{}'::jsonb,'ci-m29-job-key-002','failed',2,3),
 ('JOB-CI-M29-003','CI-M29-TASK-001','test.run','{}'::jsonb,'ci-m29-job-key-003','queued',0,3);
 insert into public.papi_worker_assignments(task_id,worker_id,job_id,required_skill,required_permission,assigned_by,status,assigned_at,started_at,finished_at)
 values
 ('CI-M29-TASK-001','CI-WORKER-M29','JOB-CI-M29-001','test.run','task.execute','ci-owner','completed',now()-interval '1 hour',now()-interval '40 minutes',now()-interval '10 minutes'),
 ('CI-M29-TASK-001','CI-WORKER-M29','JOB-CI-M29-002','test.run','task.execute','ci-owner','failed',now()-interval '1 hour',now()-interval '50 minutes',now()-interval '20 minutes'),
 ('CI-M29-TASK-001','CI-WORKER-M29','JOB-CI-M29-003','test.run','task.execute','ci-owner','assigned',now()-interval '1 hour',null,null);

 v_eval:=public.papi_supervisor_evaluate_worker('CI-WORKER-M29','supervisor-ci',now()-interval '1 day',now()+interval '1 second');
 if (v_eval->>'sample_size')::integer<>3 or (v_eval->>'completed')::integer<>1 or (v_eval->>'failed')::integer<>1
 then raise exception 'Evaluation sample or terminal counts are incorrect'; end if;
 if (v_eval->>'reliability_score')::numeric<>50 or (v_eval->>'completion_score')::numeric<>66.67
 then raise exception 'Reliability or completion score is incorrect: %',v_eval; end if;
 if (v_eval->>'overall_score')::numeric>=60 then raise exception 'Low-score alert threshold was not exercised'; end if;
 if not exists(select 1 from public.papi_supervisor_alerts where worker_id='CI-WORKER-M29' and alert_type='failure_rate' and severity='critical')
 or not exists(select 1 from public.papi_supervisor_alerts where worker_id='CI-WORKER-M29' and alert_type='low_score')
 then raise exception 'Evaluation alerts were not created'; end if;

 begin
  perform public.papi_supervisor_evaluate_worker('CI-WORKER-M29','CI-WORKER-M29',now()-interval '1 day',now()+interval '1 second');
  raise exception 'Self-evaluation was accepted';
 exception when invalid_parameter_value then null; end;

 update public.papi_worker_heartbeats set last_seen_at=now()-interval '10 minutes' where worker_id='CI-WORKER-M29';
 v_stale_count:=public.papi_supervisor_detect_stale_workers('supervisor-ci',300);
 if v_stale_count<>1 then raise exception 'Stale heartbeat was not detected'; end if;
 if public.papi_supervisor_detect_stale_workers('supervisor-ci',300)<>0 then raise exception 'Stale alert was not deduplicated'; end if;

 insert into public.papi_supervisor_alerts(alert_key,worker_id,severity,alert_type,summary,evidence,recommended_action)
 values('ci-m29-human-review-001','CI-WORKER-M29','warning','low_score','CI human review alert','{"source":"test"}'::jsonb,'review')
 on conflict(worker_id,alert_type) where status in('open','acknowledged') do nothing;
 select alert_id into v_alert_id from public.papi_supervisor_alerts where worker_id='CI-WORKER-M29' and alert_type='stale_heartbeat' and status='open';
 if v_alert_id is null then raise exception 'Stale alert not available for human acknowledgement'; end if;
 if not public.papi_supervisor_update_alert(v_alert_id,'acknowledge','human-reviewer') then raise exception 'Human acknowledgement failed'; end if;
 if public.papi_supervisor_update_alert(v_alert_id,'acknowledge','human-reviewer') then raise exception 'Duplicate acknowledgement was not idempotently rejected'; end if;
 if not public.papi_supervisor_update_alert(v_alert_id,'resolve','human-reviewer') then raise exception 'Human resolution failed'; end if;
 if not exists(select 1 from public.papi_supervisor_alerts where alert_id=v_alert_id and status='resolved' and resolved_by='human-reviewer')
 then raise exception 'Human resolution was not persisted'; end if;
 if (select status from public.papi_workers where worker_id='CI-WORKER-M29')<>'active' then raise exception 'Supervisor unexpectedly changed worker status'; end if;

 if has_table_privilege('anon','public.papi_worker_evaluations','select')
 or has_table_privilege('authenticated','public.papi_supervisor_alerts','select')
 or has_function_privilege('anon','public.papi_supervisor_evaluate_worker(text,text,timestamptz,timestamptz)','execute')
 or has_function_privilege('authenticated','public.papi_supervisor_update_alert(uuid,text,text)','execute')
 then raise exception 'Supervisor permissions are too broad'; end if;
end; $$;
