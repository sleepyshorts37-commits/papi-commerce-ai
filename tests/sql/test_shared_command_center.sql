-- Mission 31 shared command-center snapshot contract.
do $$
declare
    v_snapshot jsonb;
    v_worker text := 'CI-WORKER-M31';
    v_alert uuid;
    v_incident jsonb;
    v_rejected boolean := false;
begin
    insert into public.papi_tasks(id, task, version)
    values ('CI-M31-TASK-001', '{"id":"CI-M31-TASK-001","status":"ready"}'::jsonb, 1);
    perform public.papi_register_worker(v_worker, 'IDENTITY-CI-WORKER-M31', 'CI Worker M31',
        'market', 'Command Center Test Worker', null, array['test.run'], array['task.execute'], 2);
    perform public.papi_supervisor_heartbeat(v_worker, 'trusted_monitor');
    insert into public.papi_jobs(id, task_id, handler, payload, idempotency_key, status, attempts, max_attempts)
    values ('JOB-CI-M31-001', 'CI-M31-TASK-001', 'test.run', '{}'::jsonb, 'ci-m31-job-key-001', 'queued', 0, 3);
    insert into public.papi_supervisor_alerts(alert_key, worker_id, severity, alert_type, summary, evidence, recommended_action)
    values ('ci-m31-alert-key-001', v_worker, 'warning', 'stale_heartbeat',
        'Command center fixture alert.', '{"fixture":true}'::jsonb, 'review') returning alert_id into v_alert;
    v_incident := public.papi_incident_open_from_alert(v_alert, 'ci-m31-incident-key-001', 'human-operator');

    v_snapshot := public.papi_command_center_snapshot(10);
    if (v_snapshot->'summary'->>'workers_total')::integer < 1
       or (v_snapshot->'summary'->>'jobs_queued')::integer < 1
       or (v_snapshot->'summary'->>'alerts_open')::integer < 1
       or (v_snapshot->'summary'->>'incidents_open')::integer < 1 then
        raise exception 'Command-center summary counts are incorrect: %', v_snapshot->'summary';
    end if;
    if not exists (
        select 1 from jsonb_array_elements(v_snapshot->'workers') x
        where x->>'worker_id' = v_worker and x->>'heartbeat_source' = 'trusted_monitor'
    ) then
        raise exception 'Worker/heartbeat projection is incomplete';
    end if;
    if not exists (select 1 from jsonb_array_elements(v_snapshot->'jobs') x where x->>'id' = 'JOB-CI-M31-001')
       or not exists (select 1 from jsonb_array_elements(v_snapshot->'alerts') x where x->>'alert_id' = v_alert::text)
       or not exists (select 1 from jsonb_array_elements(v_snapshot->'incidents') x
                      where x->>'incident_key' = 'ci-m31-incident-key-001') then
        raise exception 'Job, alert or incident projection is incomplete';
    end if;
    if v_snapshot::text like '%IDENTITY-CI-WORKER-M31%'
       or v_snapshot::text like '%ci-m31-job-key-001%'
       or v_snapshot::text like '%payload%' then
        raise exception 'Command-center snapshot exposed private identity, idempotency key or payload';
    end if;
    begin
        perform public.papi_command_center_snapshot(0);
    exception when invalid_parameter_value then
        v_rejected := true;
    end;
    if not v_rejected then raise exception 'Invalid command-center limit was accepted'; end if;
    if has_function_privilege('anon', 'public.papi_command_center_snapshot(integer)', 'execute')
       or has_function_privilege('authenticated', 'public.papi_command_center_snapshot(integer)', 'execute')
       or not has_function_privilege('service_role', 'public.papi_command_center_snapshot(integer)', 'execute') then
        raise exception 'Command-center function privileges are incorrect';
    end if;
end;
$$;
