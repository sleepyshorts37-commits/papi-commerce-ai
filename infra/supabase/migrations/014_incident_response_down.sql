-- Refuse rollback when incident history exists.
do $$ begin
 if exists(select 1 from public.papi_incidents) or exists(select 1 from public.papi_incident_events)
 then raise exception 'Refusing rollback: incident history exists'; end if;
end; $$;
drop function if exists public.papi_incident_detect_overdue(text);
drop function if exists public.papi_incident_transition(uuid,text,text,text,text,jsonb,text);
drop function if exists public.papi_incident_open_from_alert(uuid,text,text);
drop function if exists public.papi_incident_sla_interval(text);
drop trigger if exists papi_incident_events_append_only on public.papi_incident_events;
drop function if exists public.papi_reject_incident_event_mutation();
drop table if exists public.papi_incident_events;
drop table if exists public.papi_incidents;
