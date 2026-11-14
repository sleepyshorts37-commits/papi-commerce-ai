-- Mission 28 SQL contract tests. Run after migration 012.
do $$
declare
    v_assignment jsonb;
    v_duplicate jsonb;
    v_claim jsonb;
    v_status text;
begin
    insert into public.papi_tasks(id, task, version)
    values ('CI-M28-TASK-001', '{"id":"CI-M28-TASK-001","status":"ready"}'::jsonb, 1);

    perform public.papi_register_worker(
        'CI-WORKER-001', 'IDENTITY-CI-WORKER-001', 'CI Worker One',
        'market', 'Order Processor', null,
        array['order.process'], array['task.execute'], 1
    );
    if not exists (select 1 from public.papi_workers
                    where worker_id='CI-WORKER-001' and status='registered') then
        raise exception 'Worker was not registered dormant';
    end if;

    begin
        perform public.papi_assign_worker_task(
            'CI-M28-TASK-001','CI-WORKER-001','order.process','task.execute',
            'ci-owner','order.process','{}'::jsonb,'ci-m28-assign-key-001'
        );
        raise exception 'Dormant worker received a task';
    exception when insufficient_privilege then
        null;
    end;

    perform public.papi_set_worker_status('CI-WORKER-001','active');

    v_assignment := public.papi_assign_worker_task(
        'CI-M28-TASK-001','CI-WORKER-001','order.process','task.execute',
        'ci-owner','order.process','{"task_ref":"CI-M28-TASK-001"}'::jsonb,'ci-m28-assign-key-001'
    );
    v_duplicate := public.papi_assign_worker_task(
        'CI-M28-TASK-001','CI-WORKER-001','order.process','task.execute',
        'ci-owner','order.process','{"task_ref":"CI-M28-TASK-001"}'::jsonb,'ci-m28-assign-key-001'
    );
    if v_assignment->>'assignment_id' <> v_duplicate->>'assignment_id' then
        raise exception 'Idempotent assignment returned a different assignment';
    end if;

    begin
        perform public.papi_assign_worker_task(
            'CI-M28-TASK-001','CI-WORKER-001','order.process','task.execute',
            'ci-owner','order.process','{}'::jsonb,'ci-m28-assign-key-002'
        );
        raise exception 'Duplicate active task assignment was accepted';
    exception when unique_violation then
        null;
    end;

    begin
        perform public.papi_assign_worker_task(
            'CI-M28-TASK-001','CI-WORKER-001','order.refund','finance.refund',
            'ci-owner','order.refund','{}'::jsonb,'ci-m28-assign-key-003'
        );
        raise exception 'Worker received a task without required permission';
    exception when insufficient_privilege then
        null;
    end;

    v_claim := public.papi_claim_worker_job('CI-WORKER-001',gen_random_uuid(),60);
    if v_claim is null or v_claim->>'task_id' <> 'CI-M28-TASK-001' then
        raise exception 'Assigned worker could not claim its own job';
    end if;

    if public.papi_finish_worker_job(
        v_claim->>'job_id','OTHER-WORKER',(v_claim->>'lease_token')::uuid,
        true,'{}'::jsonb,null
    ) <> 'stale_or_not_owned' then
        raise exception 'Another worker completed this worker job';
    end if;

    v_status := public.papi_finish_worker_job(
        v_claim->>'job_id','CI-WORKER-001',(v_claim->>'lease_token')::uuid,
        true,'{"result":"ok"}'::jsonb,null
    );
    if v_status <> 'done' then
        raise exception 'Worker job completion failed';
    end if;

    if not has_table_privilege('anon','public.papi_workers','select') = false
       or has_table_privilege('authenticated','public.papi_worker_assignments','select')
       or has_function_privilege('anon','public.papi_assign_worker_task(text,text,text,text,text,text,jsonb,text)','execute')
       or has_function_privilege('authenticated','public.papi_set_worker_status(text,text)','execute') then
        raise exception 'Worker registry permissions are too broad';
    end if;
end;
$$;
