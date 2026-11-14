-- Mission 28: governed worker registry and capacity-aware task assignment.
-- Workers remain dormant unless explicitly activated by a trusted administrator.

create table if not exists public.papi_workers (
    worker_id text primary key check (worker_id ~ '^[A-Z0-9][A-Z0-9._-]{2,119}$'),
    identity_id text not null unique check (length(identity_id) between 8 and 160),
    display_name text not null check (length(trim(display_name)) between 1 and 120),
    department text not null check (department ~ '^[a-z][a-z0-9_-]{1,79}$'),
    role_name text not null check (length(trim(role_name)) between 1 and 100),
    manager_worker_id text references public.papi_workers(worker_id) on delete restrict,
    skills text[] not null default '{}',
    permissions text[] not null default '{}',
    status text not null default 'registered'
        check (status in ('registered', 'idle', 'active', 'paused', 'disabled')),
    max_concurrency integer not null default 1 check (max_concurrency between 1 and 20),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (manager_worker_id is null or manager_worker_id <> worker_id),
    check (array_position(skills, null) is null),
    check (array_position(permissions, null) is null)
);

create index if not exists papi_workers_department_status_idx
    on public.papi_workers(department, status);
create index if not exists papi_workers_manager_idx
    on public.papi_workers(manager_worker_id);

create table if not exists public.papi_worker_assignments (
    assignment_id uuid primary key default gen_random_uuid(),
    task_id text not null references public.papi_tasks(id) on delete restrict,
    worker_id text not null references public.papi_workers(worker_id) on delete restrict,
    job_id text not null unique references public.papi_jobs(id) on delete restrict,
    required_skill text not null,
    required_permission text not null,
    assigned_by text not null,
    status text not null default 'assigned'
        check (status in ('assigned', 'running', 'completed', 'failed', 'cancelled')),
    assigned_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    check ((status in ('completed','failed','cancelled')) = (finished_at is not null))
);

create unique index if not exists papi_worker_one_active_assignment_per_task
    on public.papi_worker_assignments(task_id)
    where status in ('assigned', 'running');
create index if not exists papi_worker_assignments_worker_status_idx
    on public.papi_worker_assignments(worker_id, status, assigned_at);

alter table public.papi_workers enable row level security;
alter table public.papi_worker_assignments enable row level security;
revoke all on public.papi_workers from public, anon, authenticated;
revoke all on public.papi_worker_assignments from public, anon, authenticated;
grant select on public.papi_workers to service_role;
grant select on public.papi_worker_assignments to service_role;

-- Trusted backend registers workers. Identity IDs cannot be changed after creation.
create or replace function public.papi_register_worker(
    p_worker_id text,
    p_identity_id text,
    p_display_name text,
    p_department text,
    p_role_name text,
    p_manager_worker_id text,
    p_skills text[],
    p_permissions text[],
    p_max_concurrency integer default 1
) returns boolean
language plpgsql security definer
set search_path = public, pg_temp
as $$
begin
    if p_worker_id is null or p_identity_id is null or p_display_name is null
       or p_department is null or p_role_name is null
       or p_skills is null or p_permissions is null
       or p_max_concurrency is null or p_max_concurrency not between 1 and 20
       or cardinality(p_skills) > 100 or cardinality(p_permissions) > 100
       or exists (select 1 from unnest(p_skills || p_permissions) x
                  where x is null or length(trim(x)) = 0 or length(x) > 120)
       or p_worker_id = p_manager_worker_id then
        raise exception 'Invalid worker registration' using errcode = '22023';
    end if;
    if p_manager_worker_id is not null and not exists (
        select 1 from public.papi_workers
         where worker_id = p_manager_worker_id and status <> 'disabled'
    ) then
        raise exception 'Manager worker is missing or disabled' using errcode = '23503';
    end if;
    insert into public.papi_workers(
        worker_id, identity_id, display_name, department, role_name,
        manager_worker_id, skills, permissions, max_concurrency, status
    ) values (
        p_worker_id, p_identity_id, p_display_name, p_department, p_role_name,
        p_manager_worker_id, p_skills, p_permissions, p_max_concurrency, 'registered'
    );
    return true;
end;
$$;

-- Activation is a separate explicit administrative operation.
create or replace function public.papi_set_worker_status(
    p_worker_id text, p_status text
) returns boolean
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare v_count integer;
begin
    if p_status not in ('idle', 'active', 'paused', 'disabled') then
        raise exception 'Invalid worker status' using errcode = '22023';
    end if;
    update public.papi_workers
       set status = p_status, updated_at = now()
     where worker_id = p_worker_id;
    get diagnostics v_count = row_count;
    return v_count = 1;
end;
$$;

-- Assignment checks skills, permissions, active status and capacity atomically.
-- A new internal job is created; no external side effect is triggered.
create or replace function public.papi_assign_worker_task(
    p_task_id text,
    p_worker_id text,
    p_required_skill text,
    p_required_permission text,
    p_assigned_by text,
    p_handler text,
    p_payload jsonb,
    p_idempotency_key text
) returns jsonb
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare
    v_worker public.papi_workers%rowtype;
    v_active integer;
    v_job_id text;
    v_assignment public.papi_worker_assignments%rowtype;
begin
    if p_task_id is null or p_worker_id is null
       or p_required_skill is null or p_required_permission is null
       or p_assigned_by is null or length(trim(p_assigned_by)) not between 1 and 120
       or p_handler is null or length(trim(p_handler)) not between 1 and 100
       or p_payload is null or jsonb_typeof(p_payload) <> 'object'
       or p_idempotency_key is null or length(p_idempotency_key) not between 8 and 180 then
        raise exception 'Invalid worker assignment request' using errcode = '22023';
    end if;

    select * into v_worker
      from public.papi_workers
     where worker_id = p_worker_id
     for update;
    if not found or v_worker.status <> 'active' then
        raise exception 'Worker is not active' using errcode = '42501';
    end if;
    if not (p_required_skill = any(v_worker.skills))
       or not (p_required_permission = any(v_worker.permissions)) then
        raise exception 'Worker lacks required skill or permission' using errcode = '42501';
    end if;

    select count(*) into v_active
      from public.papi_worker_assignments
     where worker_id = p_worker_id and status in ('assigned','running');
    if v_active >= v_worker.max_concurrency then
        raise exception 'Worker capacity reached' using errcode = '54000';
    end if;

    -- Existing idempotency key must not be reused for another task/worker intent.
    select j.id into v_job_id
      from public.papi_jobs j
     where j.idempotency_key = p_idempotency_key;
    if v_job_id is not null then
        select * into v_assignment
          from public.papi_worker_assignments
         where job_id = v_job_id;
        if not found or v_assignment.task_id <> p_task_id
           or v_assignment.worker_id <> p_worker_id
           or v_assignment.required_skill <> p_required_skill
           or v_assignment.required_permission <> p_required_permission then
            raise exception 'Assignment idempotency key conflicts with another intent'
                using errcode = '23505';
        end if;
        return jsonb_build_object(
            'assignment_id', v_assignment.assignment_id,
            'job_id', v_assignment.job_id,
            'status', v_assignment.status
        );
    end if;

    v_job_id := 'JOB-' || replace(gen_random_uuid()::text, '-', '');
    insert into public.papi_jobs(
        id, task_id, handler, payload, agent_identity, idempotency_key, status, max_attempts
    ) values (
        v_job_id, p_task_id, p_handler, p_payload,
        jsonb_build_object('worker_id', v_worker.worker_id, 'identity_id', v_worker.identity_id),
        p_idempotency_key, 'queued', 5
    );

    insert into public.papi_worker_assignments(
        task_id, worker_id, job_id, required_skill, required_permission, assigned_by
    ) values (
        p_task_id, p_worker_id, v_job_id, p_required_skill, p_required_permission, p_assigned_by
    ) returning * into v_assignment;

    return jsonb_build_object(
        'assignment_id', v_assignment.assignment_id,
        'job_id', v_assignment.job_id,
        'status', v_assignment.status
    );
end;
$$;

-- Claim only jobs belonging to this worker and move assignment in the same transaction.
create or replace function public.papi_claim_worker_job(
    p_worker_id text, p_lease_token uuid, p_lease_seconds integer default 120
) returns jsonb
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare
    v_job public.papi_jobs%rowtype;
    v_assignment public.papi_worker_assignments%rowtype;
begin
    if p_worker_id is null or p_lease_token is null
       or p_lease_seconds not between 15 and 900 then
        raise exception 'Invalid worker claim request' using errcode = '22023';
    end if;
    if not exists (select 1 from public.papi_workers
                    where worker_id = p_worker_id and status = 'active') then
        raise exception 'Worker is not active' using errcode = '42501';
    end if;

    select j.* into v_job
      from public.papi_jobs j
      join public.papi_worker_assignments a on a.job_id = j.id
     where a.worker_id = p_worker_id
       and a.status in ('assigned','running')
       and (
          (j.status in ('queued','retry') and j.available_at <= now())
          or (j.status = 'running' and j.lease_until <= now())
       )
       and j.attempts < j.max_attempts
     order by j.available_at, j.created_at
     for update of j skip locked
     limit 1;
    if not found then return null; end if;

    update public.papi_jobs
       set status = 'running', attempts = attempts + 1,
           lease_owner = p_worker_id, lease_token = p_lease_token,
           lease_until = now() + make_interval(secs => p_lease_seconds),
           updated_at = now()
     where id = v_job.id
     returning * into v_job;

    update public.papi_worker_assignments
       set status = 'running', started_at = coalesce(started_at, now())
     where job_id = v_job.id
     returning * into v_assignment;

    return jsonb_build_object(
        'job_id', v_job.id, 'task_id', v_job.task_id,
        'handler', v_job.handler, 'payload', v_job.payload,
        'worker_id', p_worker_id, 'attempts', v_job.attempts,
        'lease_token', v_job.lease_token, 'lease_until', v_job.lease_until
    );
end;
$$;

create or replace function public.papi_finish_worker_job(
    p_job_id text, p_worker_id text, p_lease_token uuid,
    p_success boolean, p_result jsonb default '{}'::jsonb,
    p_error_code text default null
) returns text
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare
    v_job public.papi_jobs%rowtype;
    v_status text;
begin
    if p_job_id is null or p_worker_id is null or p_lease_token is null
       or p_success is null or p_result is null
       or jsonb_typeof(p_result) <> 'object'
       or (p_success and p_error_code is not null)
       or (not p_success and (p_error_code is null or p_error_code !~ '^[a-z0-9_]{1,80}$')) then
        raise exception 'Invalid worker completion request' using errcode = '22023';
    end if;

    select * into v_job
      from public.papi_jobs
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now()
     for update;
    if not found then return 'stale_or_not_owned'; end if;

    if p_success then
        v_status := 'done';
        update public.papi_jobs
           set status = 'done', result = p_result, updated_at = now(),
               lease_owner = null, lease_token = null, lease_until = null
         where id = p_job_id;
        update public.papi_worker_assignments
           set status = 'completed', finished_at = now()
         where job_id = p_job_id and worker_id = p_worker_id;
    elsif v_job.attempts >= v_job.max_attempts then
        v_status := 'failed';
        update public.papi_jobs
           set status = 'failed', last_error_code = p_error_code, updated_at = now(),
               lease_owner = null, lease_token = null, lease_until = null
         where id = p_job_id;
        update public.papi_worker_assignments
           set status = 'failed', finished_at = now()
         where job_id = p_job_id and worker_id = p_worker_id;
    else
        v_status := 'retry';
        update public.papi_jobs
           set status = 'retry', last_error_code = p_error_code,
               available_at = now() + make_interval(secs => least(3600, 15 * power(2, attempts - 1)::integer)),
               updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
         where id = p_job_id;
        update public.papi_worker_assignments
           set status = 'assigned'
         where job_id = p_job_id and worker_id = p_worker_id;
    end if;
    return v_status;
end;
$$;

revoke all on function public.papi_register_worker(text,text,text,text,text,text,text[],text[],integer)
    from public, anon, authenticated;
revoke all on function public.papi_set_worker_status(text,text)
    from public, anon, authenticated;
revoke all on function public.papi_assign_worker_task(text,text,text,text,text,text,jsonb,text)
    from public, anon, authenticated;
revoke all on function public.papi_claim_worker_job(text,uuid,integer)
    from public, anon, authenticated;
revoke all on function public.papi_finish_worker_job(text,text,uuid,boolean,jsonb,text)
    from public, anon, authenticated;
grant execute on function public.papi_register_worker(text,text,text,text,text,text,text[],text[],integer) to service_role;
grant execute on function public.papi_set_worker_status(text,text) to service_role;
grant execute on function public.papi_assign_worker_task(text,text,text,text,text,text,jsonb,text) to service_role;
grant execute on function public.papi_claim_worker_job(text,uuid,integer) to service_role;
grant execute on function public.papi_finish_worker_job(text,text,uuid,boolean,jsonb,text) to service_role;
