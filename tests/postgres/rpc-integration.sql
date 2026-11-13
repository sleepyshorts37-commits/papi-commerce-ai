-- Integration tests for all PAPI RPCs. Runs only against disposable CI PostgreSQL.
\set ON_ERROR_STOP on

do $$
declare
  v_version bigint;
  v_claim jsonb;
  v_claim2 jsonb;
  v_token uuid := '11111111-1111-4111-8111-111111111111';
  v_token2 uuid := '22222222-2222-4222-8222-222222222222';
  v_status text;
  v_ok boolean;
begin
  -- Task commit: valid optimistic update and atomic audit event.
  insert into public.papi_tasks(id, task, version)
  values ('CI-TASK-1', '{"id":"CI-TASK-1","status":"backlog"}', 1);
  v_version := public.papi_commit_task_change(
    'CI-TASK-1', 1,
    '{"id":"CI-TASK-1","status":"ready"}',
    jsonb_build_object(
      'event_id','CI-EVENT-1','occurred_at',now(),'actor','ci',
      'action','task.ready','entity_type','task','entity_id','CI-TASK-1',
      'details',jsonb_build_object('source','integration-test')
    )
  );
  if v_version <> 2 then raise exception 'commit_task_change returned wrong version'; end if;
  if not exists(select 1 from public.papi_audit_events where event_id='CI-EVENT-1') then
    raise exception 'audit event was not committed atomically';
  end if;

  -- Stale version and malformed payload must be rejected.
  begin
    perform public.papi_commit_task_change(
      'CI-TASK-1', 1, '{"id":"CI-TASK-1","status":"done"}',
      jsonb_build_object('event_id','CI-EVENT-STALE','occurred_at',now(),'actor','ci',
        'action','task.done','entity_type','task','entity_id','CI-TASK-1','details','{}'::jsonb)
    );
    raise exception 'stale task version unexpectedly succeeded';
  exception when sqlstate '40001' then null;
  end;
  begin
    perform public.papi_commit_task_change('CI-TASK-1',2,'[]','{}');
    raise exception 'invalid task payload unexpectedly succeeded';
  exception when sqlstate '22023' then null;
  end;
  if exists(select 1 from public.papi_audit_events where event_id='CI-EVENT-STALE') then
    raise exception 'failed task update left an audit event';
  end if;

  -- Claim: only one available job is leased; invalid lease request is rejected.
  insert into public.papi_jobs(id,task_id,handler,idempotency_key,max_attempts)
  values ('CI-JOB-1','CI-TASK-1','ci.echo','CI-IDEM-1',2);
  v_claim := public.papi_claim_job('ci-worker-1',v_token,60);
  if v_claim is null or v_claim->>'id' <> 'CI-JOB-1' or (v_claim->>'attempts')::int <> 1 then
    raise exception 'claim_job did not lease the expected job';
  end if;
  v_claim2 := public.papi_claim_job('ci-worker-2',v_token2,60);
  if v_claim2 is not null then raise exception 'same queued job was leased twice'; end if;
  begin
    perform public.papi_claim_job(' ',v_token2,60);
    raise exception 'invalid worker unexpectedly accepted';
  exception when sqlstate '22023' then null;
  end;

  -- Complete: wrong owner/token returns false; valid lease completes.
  v_ok := public.papi_complete_job('CI-JOB-1','ci-worker-2',v_token,'{"ok":true}');
  if v_ok then raise exception 'wrong worker completed a job'; end if;
  v_ok := public.papi_complete_job('CI-JOB-1','ci-worker-1',v_token,'{"ok":true}');
  if not v_ok then raise exception 'valid lease could not complete job'; end if;
  if (select status from public.papi_jobs where id='CI-JOB-1') <> 'done' then
    raise exception 'job status did not become done';
  end if;
  begin
    perform public.papi_complete_job('CI-JOB-1','ci-worker-1',v_token,'null'::jsonb);
    raise exception 'null completion result unexpectedly accepted';
  exception when sqlstate '22023' then null;
  end;

  -- Fail: first attempt retries, second attempt becomes terminal.
  insert into public.papi_jobs(id,task_id,handler,idempotency_key,max_attempts)
  values ('CI-JOB-2','CI-TASK-1','ci.echo','CI-IDEM-2',2);
  v_claim := public.papi_claim_job('ci-worker-1',v_token,60);
  if v_claim->>'id' <> 'CI-JOB-2' then raise exception 'second job was not claimed'; end if;
  begin
    perform public.papi_fail_job('CI-JOB-2','ci-worker-wrong',v_token,'temporary_error');
    raise exception 'failure with wrong worker unexpectedly succeeded';
  exception when sqlstate '40001' then null;
  end;
  v_status := public.papi_fail_job('CI-JOB-2','ci-worker-1',v_token,'temporary_error');
  if v_status <> 'retry' then raise exception 'first failure should schedule retry'; end if;
  update public.papi_jobs set available_at=now() where id='CI-JOB-2';
  v_claim := public.papi_claim_job('ci-worker-1',v_token2,60);
  if v_claim->>'id' <> 'CI-JOB-2' or (v_claim->>'attempts')::int <> 2 then
    raise exception 'retry attempt was not claimed';
  end if;
  v_status := public.papi_fail_job('CI-JOB-2','ci-worker-1',v_token2,'permanent_error');
  if v_status <> 'failed' then raise exception 'max attempts should make job terminal'; end if;

  -- Expired lease is reclaimable with a new token.
  insert into public.papi_jobs(id,task_id,handler,idempotency_key,max_attempts)
  values ('CI-JOB-3','CI-TASK-1','ci.echo','CI-IDEM-3',3);
  v_claim := public.papi_claim_job('ci-worker-1',v_token,60);
  if v_claim->>'id' <> 'CI-JOB-3' then raise exception 'third job was not claimed'; end if;
  update public.papi_jobs set lease_until=now()-interval '1 second' where id='CI-JOB-3';
  v_claim := public.papi_claim_job('ci-worker-2',v_token2,60);
  if v_claim->>'id' <> 'CI-JOB-3' or (v_claim->>'lease_token') <> v_token2::text then
    raise exception 'expired lease was not reclaimed';
  end if;

  -- Nonce: only an active key version may consume a nonce; replay is rejected.
  insert into public.papi_agent_public_keys(agent_id, key_version, public_key_hex, status)
  values ('ci-agent', 1, repeat('a', 64), 'active');
  v_ok := public.papi_consume_agent_nonce(
    'ci-agent', 1, 'nonce-integration-000001', now()+interval '5 minutes'
  );
  if not v_ok then raise exception 'first nonce use with active key was rejected'; end if;
  v_ok := public.papi_consume_agent_nonce(
    'ci-agent', 1, 'nonce-integration-000001', now()+interval '5 minutes'
  );
  if v_ok then raise exception 'nonce replay was accepted'; end if;
  v_ok := public.papi_consume_agent_nonce(
    'missing-ci-agent', 1, 'nonce-missing-key-000001', now()+interval '5 minutes'
  );
  if v_ok then raise exception 'nonce without active key was accepted'; end if;
  insert into public.papi_agent_public_keys(
    agent_id, key_version, public_key_hex, status, revoked_at
  ) values ('ci-agent', 2, repeat('b', 64), 'revoked', now());
  v_ok := public.papi_consume_agent_nonce(
    'ci-agent', 2, 'nonce-revoked-key-0001', now()+interval '5 minutes'
  );
  if v_ok then raise exception 'nonce with revoked key version was accepted'; end if;
  if to_regprocedure('public.papi_consume_agent_nonce(text,text,timestamptz)') is not null then
    raise exception 'legacy three-argument nonce RPC still exists';
  end if;
  begin
    perform public.papi_consume_agent_nonce(
      'ci-agent', 1, 'short', now()+interval '5 minutes'
    );
    raise exception 'short nonce unexpectedly accepted';
  exception when sqlstate '22023' then null;
  end;
end;
$$;
