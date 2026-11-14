-- Mission 27 PostgreSQL contracts. Run after migration 011 on a disposable database.
do $$
declare
    v_id uuid;
    v_duplicate uuid;
    v_claim jsonb;
    v_second jsonb;
    v_status text;
    v_attempts integer;
    v_count integer;
begin
    v_id := public.papi_enqueue_outbox(
        'ci-m27-order-confirm-001', 'order.confirmed', 'ORDER-CI-M27-001',
        '{"order_ref":"ORDER-CI-M27-001","customer_ref":"CUSTOMER-REF-ONLY"}'::jsonb, 3
    );
    v_duplicate := public.papi_enqueue_outbox(
        'ci-m27-order-confirm-001', 'order.confirmed', 'ORDER-CI-M27-001',
        '{"order_ref":"ORDER-CI-M27-001","customer_ref":"CUSTOMER-REF-ONLY"}'::jsonb, 3
    );
    if v_id <> v_duplicate then
        raise exception 'Same idempotency key did not return the original outbox ID';
    end if;

    begin
        perform public.papi_enqueue_outbox(
            'ci-m27-order-confirm-001', 'order.cancelled', 'ORDER-CI-M27-001',
            '{"order_ref":"ORDER-CI-M27-001"}'::jsonb, 3
        );
        raise exception 'Idempotency key accepted different business intent';
    exception when unique_violation then
        null;
    end;

    v_claim := public.papi_claim_outbox('ci-m27-worker-a', gen_random_uuid(), 60);
    if v_claim is null or (v_claim->>'id')::uuid <> v_id
       or (v_claim->>'attempts')::integer <> 1 then
        raise exception 'First outbox claim failed';
    end if;

    if public.papi_finish_outbox(
        v_id, 'other-worker', (v_claim->>'lease_token')::uuid, true, null
    ) <> 'stale_or_not_owned' then
        raise exception 'Different worker completed an outbox event';
    end if;
    if public.papi_finish_outbox(
        v_id, 'ci-m27-worker-a', gen_random_uuid(), true, null
    ) <> 'stale_or_not_owned' then
        raise exception 'Wrong lease token completed an outbox event';
    end if;

    v_status := public.papi_finish_outbox(
        v_id, 'ci-m27-worker-a', (v_claim->>'lease_token')::uuid, false, 'provider_timeout'
    );
    if v_status <> 'retry' then
        raise exception 'Expected retry state, got %', v_status;
    end if;

    update public.papi_outbox set available_at = now() - interval '1 second'
     where id = v_id and status = 'retry';
    v_claim := public.papi_claim_outbox('ci-m27-worker-b', gen_random_uuid(), 60);
    if v_claim is null or (v_claim->>'attempts')::integer <> 2 then
        raise exception 'Retry claim did not increment attempt count';
    end if;

    v_status := public.papi_finish_outbox(
        v_id, 'ci-m27-worker-b', (v_claim->>'lease_token')::uuid, true, null
    );
    if v_status <> 'delivered' then
        raise exception 'Successful acknowledgement did not mark delivered';
    end if;

    if public.papi_finish_outbox(
        v_id, 'ci-m27-worker-b', (v_claim->>'lease_token')::uuid, true, null
    ) <> 'stale_or_not_owned' then
        raise exception 'Duplicate acknowledgement was not rejected';
    end if;

    select count(*) into v_count from public.papi_outbox_attempts
     where outbox_id = v_id
       and event_type in ('claimed', 'retry_scheduled', 'delivered');
    if v_count <> 4 then
        raise exception 'Expected four attempt events, got %', v_count;
    end if;

    -- Exhausted event becomes terminal on the last failed attempt.
    v_duplicate := public.papi_enqueue_outbox(
        'ci-m27-order-failed-002', 'order.receipt.ready', 'ORDER-CI-M27-002',
        '{"order_ref":"ORDER-CI-M27-002"}'::jsonb, 1
    );
    v_claim := public.papi_claim_outbox('ci-m27-worker-c', gen_random_uuid(), 60);
    if v_claim is null or (v_claim->>'id')::uuid <> v_duplicate then
        raise exception 'Second event was not claimable';
    end if;
    v_status := public.papi_finish_outbox(
        v_duplicate, 'ci-m27-worker-c', (v_claim->>'lease_token')::uuid, false, 'permanent_reject'
    );
    if v_status <> 'dead_letter' then
        raise exception 'Exhausted event did not enter dead_letter';
    end if;

    -- Expired lease is reclaimed with a fresh fencing token.
    v_duplicate := public.papi_enqueue_outbox(
        'ci-m27-lease-reclaim-003', 'inventory.updated', 'SKU-CI-M27-003',
        '{"sku_ref":"SKU-CI-M27-003"}'::jsonb, 3
    );
    v_claim := public.papi_claim_outbox('ci-m27-worker-d', gen_random_uuid(), 60);
    if v_claim is null or (v_claim->>'id')::uuid <> v_duplicate then
        raise exception 'Lease-reclaim event was not claimed';
    end if;
    update public.papi_outbox set lease_until = now() - interval '1 second'
     where id = v_duplicate and status = 'processing';
    v_second := public.papi_claim_outbox('ci-m27-worker-e', gen_random_uuid(), 60);
    if v_second is null or (v_second->>'id')::uuid <> v_duplicate
       or v_second->>'lease_token' = v_claim->>'lease_token' then
        raise exception 'Expired lease was not reclaimed with a new token';
    end if;
    if public.papi_finish_outbox(
        v_duplicate, 'ci-m27-worker-d', (v_claim->>'lease_token')::uuid, true, null
    ) <> 'stale_or_not_owned' then
        raise exception 'Previous lease owner was not fenced out';
    end if;
    if public.papi_finish_outbox(
        v_duplicate, 'ci-m27-worker-e', (v_second->>'lease_token')::uuid, true, null
    ) <> 'delivered' then
        raise exception 'New lease owner could not finish event';
    end if;

    if not has_table_privilege('service_role', 'public.papi_outbox', 'update')
       or not has_table_privilege('service_role', 'public.papi_outbox_attempts', 'insert')
       or has_table_privilege('anon', 'public.papi_outbox', 'select')
       or has_table_privilege('authenticated', 'public.papi_outbox_attempts', 'select')
       or has_table_privilege('service_role', 'public.papi_outbox_attempts', 'update')
       or has_table_privilege('service_role', 'public.papi_outbox_attempts', 'delete')
       or has_function_privilege('anon',
          'public.papi_claim_outbox(text,uuid,integer)', 'execute')
       or has_function_privilege('authenticated',
          'public.papi_finish_outbox(uuid,text,uuid,boolean,text)', 'execute') then
        raise exception 'Outbox privileges are too broad or incomplete';
    end if;

    -- The business mutation and outbox insert roll back together when kept
    -- inside the same PostgreSQL transaction boundary.
    begin
        insert into public.papi_tasks(id, task, version)
        values (
            'CI-M27-ATOMIC-TASK',
            '{"id":"CI-M27-ATOMIC-TASK","status":"created"}'::jsonb,
            1
        );
        perform public.papi_enqueue_outbox(
            'ci-m27-atomic-rollback-004', 'task.created',
            'CI-M27-ATOMIC-TASK', '{"task_ref":"CI-M27-ATOMIC-TASK"}'::jsonb, 2
        );
        raise exception 'force transaction rollback';
    exception when raise_exception then
        null;
    end;
    if exists (select 1 from public.papi_tasks where id = 'CI-M27-ATOMIC-TASK')
       or exists (select 1 from public.papi_outbox
                   where idempotency_key = 'ci-m27-atomic-rollback-004') then
        raise exception 'Business write and outbox intent did not roll back together';
    end if;

    -- Incomplete lease metadata is invalid for every status.
    begin
        insert into public.papi_outbox(
            idempotency_key, event_type, aggregate_id, payload,
            status, lease_owner
        ) values (
            'ci-m27-invalid-lease-005', 'test.invalid', 'INVALID-LEASE',
            '{}'::jsonb, 'pending', 'orphan-worker'
        );
        raise exception 'Incomplete lease state was accepted';
    exception when check_violation then
        null;
    end;

    perform public.papi_outbox_health();
end;
$;
